# Mission 064 — Official CLI and Version-Promotion Findings

## Sources inspected

| Source | URL | Read-only finding |
|---|---|---|
| Scraper Studio development guide | https://docs.brightdata.com/datasets/scraper-studio/develop-a-scraper | Preview tests interaction, parser, output structure, and errors before production. Existing scrapers use **Save to production** to apply changes. |
| Collection and delivery guide | https://docs.brightdata.com/datasets/scraper-studio/initiate-collection-and-delivery-options | IDE work auto-saves as a **development draft**; existing production scrapers require **Save to production**. Unsaved draft scrapers cannot be initiated outside the IDE. |
| Self-Healing tool guide | https://docs.brightdata.com/datasets/scraper-studio/self-healing-tool | Self-Healing requires a scraper saved in development mode; the AI produces a diff; **Accept** saves to draft; Preview follows; **Save to Production** makes the refactored scraper live. Accepted changes affect production only after Save to Production. |
| CLI build guide | https://docs.brightdata.com/datasets/scraper-studio/build-with-the-cli | `scraper run` executes an existing stable collector ID; heal stops at `awaiting_approval` by default; `scraper approve` commits the existing scraper fix and its documented next step is a verification run. |
| CLI command reference | https://docs.brightdata.com/cli/commands | Current published `scraper run` reference lists output flags only and does not document `--version`. Its `scraper approve` reference documents reject, URL, timeout, and output flags, but does not list `--auto-save`. |
| Official CLI releases | https://github.com/brightdata/cli/releases | v0.2.0 release notes list `scraper run` flag `--version`; v0.3.2 release notes state `--auto-save` on `scraper approve` and `scraper heal --auto-approve` persists a healed template after completion; v0.3.5 is the latest listed release. |

## Version-explicit CLI conclusion

The retained project record establishes that CLI **0.3.5** was installed on demand in Mission 033. A first combined alias/help invocation became unresponsive and was terminated without a provider operation. Mission 064 then executed only version-pinned `npx --yes -p @brightdata/cli@0.3.5 bdata ... --help` commands. Both completed locally.

The exact **0.3.5** `scraper run` help confirms `--version <version>` with the description **`Scraper version (e.g. "dev")`**. The exact **0.3.5** `scraper approve` help confirms `--auto-save` with the description **`Save the approved template automatically once the job completes successfully (sent as auto_save to the resume call).`** It also documents that `approve` handles a heal awaiting approval and accepts `--reject`, `--url`, `--timeout`, and output flags.

The official release evidence independently supports `--version <explicit_version>` as a future version-bound run flag and confirms that `--auto-save` was added in v0.3.2 for approval-side template persistence. The current published command-reference pages do not list these two flags, so the version-pinned 0.3.5 local help transcript is the controlling command-syntax evidence for this preparation. Every future live preflight must re-run version-pinned local help and fail closed if the exact expected flag is absent.

## Safety interpretation

The official UI documentation establishes the following workflow: **development draft → Self-Healing diff → accepted draft → preview → Save to Production → production run**. This documentation is authoritative for the *documented workflow*, but it does not prove a specific current collector’s draft ID, version ID, template ID, or production binding. Such values remain direct-evidence requirements for any future provider operation.

## References

[1]: https://docs.brightdata.com/datasets/scraper-studio/develop-a-scraper
[2]: https://docs.brightdata.com/datasets/scraper-studio/initiate-collection-and-delivery-options
[3]: https://docs.brightdata.com/datasets/scraper-studio/self-healing-tool
[4]: https://docs.brightdata.com/datasets/scraper-studio/build-with-the-cli
[5]: https://docs.brightdata.com/cli/commands
[6]: https://github.com/brightdata/cli/releases
