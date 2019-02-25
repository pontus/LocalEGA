package se.nbis.lega.cucumber.steps;

import com.github.dockerjava.api.exception.ConflictException;
import com.github.dockerjava.api.exception.InternalServerErrorException;
import cucumber.api.java8.En;
import lombok.extern.slf4j.Slf4j;
import org.assertj.core.api.Assertions;
import org.junit.Assert;
import se.nbis.lega.cucumber.Context;
import se.nbis.lega.cucumber.Utils;
import se.nbis.lega.cucumber.pojo.FileStatus;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.concurrent.TimeoutException;
import java.util.stream.Collectors;

@Slf4j
public class Ingestion implements En {

    private static final List<FileStatus> TERMINAL_STATUSES = Arrays.asList(FileStatus.COMPLETED, FileStatus.ERROR, FileStatus.UNDEFINED);

    public Ingestion(Context context) {
        Utils utils = context.getUtils();

        Given("^I have CEGA MQ username and password$", () -> {
            context.setCegaMQUser(utils.getProperty("cega.user"));
            context.setCegaMQPassword(utils.getProperty("cega.password"));
            context.setCegaMQVHost(utils.getProperty("instance.name"));
            context.setRoutingKey(utils.getProperty("instance.name"));
            context.setCegaMQPort(utils.getProperty("cega.port"));
        });

        When("^I turn off the keyserver$", () -> utils.stopContainer(utils.findContainer(utils.getProperty("container.label.keys"))));

        When("^I turn on the keyserver$", () -> utils.startContainer(utils.findContainer(utils.getProperty("container.label.keys"))));

        When("^I turn off the database", () -> utils.stopContainer(utils.findContainer(utils.getProperty("container.label.db"))));

        When("^I turn on the database", () -> utils.startContainer(utils.findContainer(utils.getProperty("container.label.db"))));

        When("^I turn off the message broker", () -> utils.stopContainer(utils.findContainer(utils.getProperty("container.label.mq"))));

        When("^I turn on the message broker", () -> utils.startContainer(utils.findContainer(utils.getProperty("container.label.mq"))));

        When("^I ingest file from the LocalEGA inbox$", () -> {
            ingestFile(context);
        });

        Then("^I retrieve ingestion information", () -> {
            try {
                String output = utils.executeDBQuery(String.format("select * from local_ega.files where inbox_path = '%s'", context.getEncryptedFile().getName()));
                List<String> header = Arrays.stream(output.split(System.getProperty("line.separator"))[0].split(" \\| ")).map(String::trim).collect(Collectors.toList());
                List<String> fields = Arrays.stream(output.split(System.getProperty("line.separator"))[2].split(" \\| ")).map(String::trim).collect(Collectors.toList());
                HashMap<String, String> ingestionInformation = new HashMap<>();
                for (int i = 0; i < header.size(); i++) {
                    ingestionInformation.put(header.get(i), fields.get(i));
                }
                context.setIngestionInformation(ingestionInformation);
            } catch (IndexOutOfBoundsException e) {
                context.setIngestionInformation(Collections.singletonMap("status", "NoEntry"));
            } catch (InterruptedException | IOException e) {
                log.error(e.getMessage(), e);
                Assert.fail(e.getMessage());
            }
        });

        Then("^the ingestion status is \"([^\"]*)\"$", (String status) -> Assertions.assertThat(context.getIngestionInformation().get("status")).isEqualToIgnoringCase(status));

    }

    private void ingestFile(Context context) {
        try {
            Utils utils = context.getUtils();
            utils.publishCEGA(String.format("amqp://%s:%s@localhost:%s/%s",
                    context.getCegaMQUser(),
                    context.getCegaMQPassword(),
                    context.getCegaMQPort(),
                    context.getCegaMQVHost()),
                    context.getUser(),
                    context.getEncryptedFile().getName());
            // It may take a while for relatively big files to be ingested.
            // So we wait until ingestion status changes to something different from "In progress".
            long maxTimeout = Long.parseLong(utils.getProperty("ingest.max-timeout"));
            long timeout = 0;
            while (!TERMINAL_STATUSES.contains(getIngestionStatus(context, utils))) {
                Thread.sleep(1000);
                timeout += 1000;
                if (timeout > maxTimeout) {
                    throw new TimeoutException(String.format("Ingestion didn't complete in time: ingest.max-timeout = %s", maxTimeout));
                }
            }
            // And we sleep one more second for entry to be updated in the database.
            Thread.sleep(1000);
        } catch (Exception e) {
            log.error(e.getMessage(), e);
            Assert.fail(e.getMessage());
        }
    }

    private FileStatus getIngestionStatus(Context context, Utils utils) throws IOException, InterruptedException {
        try {
            String output = utils.executeDBQuery(String.format("select status from local_ega.files where inbox_path = '%s'", context.getEncryptedFile().getName()));
            return FileStatus.getValue(output.split(System.getProperty("line.separator"))[2].trim());
        } catch (InternalServerErrorException | ConflictException e) {
            return FileStatus.ERROR;
        }
    }

}