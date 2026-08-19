# Product Brief — Tag Index

## What it is

A tiny dependency-free CommonJS library that other Node scripts require to keep an
in-memory index of tags. There is no user interface, no network access, no
persistence, and no command-line entry point — it is a library other code calls.

## Who it's for

Script authors who need to group short string tags without pulling in a dependency.

## Features

- **Add a tag to a group.** The caller passes a group name and a tag; the library
  records the tag under that group and reports how many tags the group now holds.
- **List a group's tags.** The caller passes a group name and gets that group's tags
  back in the order they were added. An unknown group returns an empty list.
- **List the group names**, in the order the groups were first created.

## Success criteria

- Adding two tags to one group and listing that group returns both tags in order.
- Listing a group that was never created returns an empty list rather than failing.
- After adding tags to two groups, listing the group names returns both, oldest first.

## Notes

- Node 18+, CommonJS, no dependencies, no configuration.
- Duplicate tags inside one group are out of scope for now.
