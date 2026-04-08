# Conventional Commit

Generate and apply a conventional commit message from staged changes.

## Steps

1. Run `git diff --staged` to see what's staged. If nothing is staged, tell the user and stop.

2. Analyze the diff and determine:
   - **type**: one of `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `ci`
   - **scope** (optional): the module or area affected, in parentheses — e.g. `feat(scraper):`
   - **breaking change**: if the change breaks backwards compatibility, append `!` after type/scope and add a `BREAKING CHANGE:` footer
   - **subject**: short imperative description, lowercase, no period

3. Format the message:
   ```
   <type>[(<scope>)][!]: <subject>

   [optional body]

   [BREAKING CHANGE: <description>]
   ```

4. Show the proposed commit message to the user and ask: **"Commit with this message? (y/n/edit)"**
   - `y` — run `git commit -m "<message>"`
   - `n` — abort
   - `edit` — ask the user to provide the final message, then commit with it

## Type guide

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `chore` | Maintenance, dependencies, config |
| `docs` | Documentation only |
| `refactor` | Code restructure, no behavior change |
| `test` | Adding or fixing tests |
| `style` | Formatting, whitespace, no logic change |
| `ci` | CI/CD pipeline changes |
