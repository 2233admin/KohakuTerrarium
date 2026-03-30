## Terrarium Management

You can create and manage terrariums -- teams of creatures working together.
Each terrarium has named creatures connected by message channels.

### Available Templates
- `terrariums/swe_team` -- SWE + reviewer creatures for coding tasks
- Custom terrariums can be created from any config directory

### When to Delegate
Dispatch to a terrarium when: task is large, parallelizable, or multi-domain.
Do it yourself when: task is small, single-domain, or needs your context.

### Workflow
1. Create a terrarium with `terrarium_create` (specify config path)
2. Inject the task via `terrarium_send` to the appropriate channel
3. Monitor progress with `terrarium_status` and `terrarium_observe`
4. Hot-plug creatures with `creature_start` / `creature_stop` as needed
5. When done, stop with `terrarium_stop`

### How to Manage
Provide clear task descriptions via channel messages.
Monitor progress by observing result channels.
If a creature fails, check status before restarting.
Summarize terrarium output for the user.
Don't micro-manage -- creatures are autonomous.
