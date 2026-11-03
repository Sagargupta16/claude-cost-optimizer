# Notes

`fetch_user` is the only way the rest of the code reads a user. `service.greeting`
and `cli.main` both call `fetch_user`, so any change to its return shape needs
both of them updated.
