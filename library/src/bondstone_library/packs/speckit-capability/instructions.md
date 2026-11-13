- A feature is the record of one change; the capabilities are what stays true afterwards.
  When a feature changes behaviour, update the capability in the same change and list it
  under `modifies` in the feature's frontmatter.
- A requirement the feature will implement is added to its capability with `Status: planned`
  and listed under `delivers`. When the code is there and tagged, run
  `bondstone status REQ-... active`.
- Before you tick the last task of a feature, check that every requirement under `delivers`
  is active and tagged in code: from that tick on the feature is `implemented`.
