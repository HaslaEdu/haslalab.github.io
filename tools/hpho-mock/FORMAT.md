# HPhO sample papers: source format

Each problem has four files in `tools/hpho-mock/<set>/`:
`T1.ko.md`, `T1.en.md` (problem + answer sheet) and `T1.sol.ko.md`, `T1.sol.en.md` (solution + marking scheme).
The Korean and English files have the same blocks in the same order. `node tools/hpho-mock/build.mjs <set>` writes
`hpho/samples/<set>/<lang>/*.pdf`.

## Front matter

    id: T1
    kind: theory            theory | experiment
    no: 1
    title: Why does an hourglass run steadily?
    points: 10.0
    worksheets: 15          blank working pages after the answer sheet (problem files only)
    ---

## Blocks (separated by blank lines)

    ## Part A - Why a water clock slows down (1.2 pt)      part heading
    ### Model                                              small heading
    #### SOLUTION:                                         gold heading (solution files)
    - item                                                 bullet list (consecutive lines)
    $$ ... $$                                              display math, may span lines
    ---page---                                             page break
    ::: q A.1 0.5pt          question box (blocks inside, closed by :::)
    ::: a A.1 0.5pt 40mm     answer box on the answer sheet, with a minimum height
    ::: table                rows "| a | b |", optional last line "Caption: ..."; "::: table grid" draws every rule
    ::: figure               lines "![sub-caption](fig/file.svg 40%)", optional last line "Caption: ..."
    ::: box Title            framed box with a bold title (e.g. general marking rules)
    ::: marking              rows "| what earns the marks | 0.3 |" (solution files)
    ::: small                small grey paragraph
    === answer               everything after this goes on the answer sheet

Inline: `$...$` math, `**bold**`, `*italic*`. Math is KaTeX: use `\mathrm{}` for units, `\,` for thin spaces.
Figures are per language: `fig/T1-1a.ko.svg` and `fig/T1-1a.en.svg` (PNG/JPG also work).
