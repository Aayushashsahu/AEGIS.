# Mission 034 approval-boundary amendment — official interface findings

**Scope:** Documentation and controlled-fixture design only. This record does not authorize or execute provider approval, rerun, heal, collector creation, commit, or rollback.

| Topic | Official finding | AEGIS implication |
| --- | --- | --- |
| CLI credential interface | The Bright Data CLI supports `BRIGHTDATA_API_KEY`, local credential storage, and device/API-key login. | The future CLI-backed adapter must expose one server-side canonical credential interface and must never expose or record the value. |
| DCA collector API | Scraper Studio collection trigger/retrieval uses a bearer `BRIGHT_DATA_API_TOKEN` with `POST /dca/trigger` and `GET /dca/dataset`. | A DCA token is not evidence that a future CLI approval boundary is authenticated or authorized. |
| CLI approval capability | The official CLI documents a scraper approval command as part of self-healing. | The frozen Mission 004 contract does not expose this operation. This amendment defines a fixture-only future adapter boundary; it must not invoke a real command. |
| Read-only collector lookup | The reviewed official quickstart documents trigger and dataset retrieval, not a harmless collector metadata lookup used by the canonical adapter. | Target-collector access remains `UNKNOWN` unless a separately documented read-only operation is approved and verified. |

## Sources

[1]: https://docs.brightdata.com/cli/installation "Bright Data CLI installation and authentication"
[2]: https://docs.brightdata.com/cli/commands "Bright Data CLI command reference"
[3]: https://docs.brightdata.com/datasets/scraper-studio/build-with-the-cli "Build a scraper with the Bright Data CLI"
[4]: https://docs.brightdata.com/datasets/scraper-studio/quickstart "Bright Data Scraper Studio API quickstart"
