- Code is traced to requirements by `bondstone: REQ-...` comments. When you change code under
  such a comment, update the capability that holds the requirement in the same change.
  `bondstone context --for <paths>` lists the capabilities a file is traced to.
- A change that alters no behaviour, such as a rename or a reformat, may carry the commit
  trailer `Spec-Impact: none (<reason>)` instead. Add it only when the user asks for it.
