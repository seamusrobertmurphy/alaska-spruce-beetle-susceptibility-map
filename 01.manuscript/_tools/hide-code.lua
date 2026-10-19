-- Drops echoed source code and printed console output from a render, keeping figures, tables and prose.
-- Used for the review copy only: quarto render manuscript.qmd --to docx --output manuscript_submission.docx --lua-filter _tools/hide-code.lua
function CodeBlock(el)
  if el.classes:includes("cell-code") then return {} end
end

function Div(el)
  if el.classes:includes("cell-output-stdout") or el.classes:includes("cell-output-stderr") then return {} end
end
