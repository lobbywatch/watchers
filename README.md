# Lobbywatch Resources

## Prototype Based on `urlwatch`

`urlwatch` is a command-line utility which allows checking for changes to web pages. The state (from previous runs) is by default persisted in a SQLite database (Redis being the other alternative).

For Lobbywatch the idea is to run the tool periodically (e.g. once per day) and notify the team using a dedicated Slack channel.

As an additional benefit the Slack notifications should also highlight the names matching persons (and parlamentarians) in the Lobbywatch database.

### Usage

1. Research the page to add and figure out what CSS selector to apply
2. Add the page definition to `urls-test.yaml` and test the output using `./urlwatch-test.sh`
3. Once satisfied transfer the page to `urls.yaml` and run `./urlwatch-import.sh <n>` where `<n>` is the job number
4. Finally run `./urlwatch.sh` which will send a Slack notification

Periodically the name list for the name matching should also be updated. This can be done using the `load-personen.sh` script.