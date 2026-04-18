# Output Contract Rules (v1)

Follow any output contract requested by the caller.
If no explicit contract is requested, respond with plain assistant text.

For revision proposals:
- keep code edits inside revision_request.patch_contract.operations
- do not output ad-hoc raw overwrite content outside patch contract fields
