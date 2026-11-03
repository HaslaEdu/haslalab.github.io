// Official external reading references, separate from the digital-question index.
// An entry here never creates a canonical source or claims imported questions.
// URLs and volume topics were checked against the primary sites on 2026-11-04.
export const ARCHIVE_BOOK_REFERENCES = Object.freeze([
  {
    id: 'goldstein-classical-mechanics',
    title: {ko: 'Classical Mechanics Goldstein', en: 'Classical Mechanics Goldstein'},
    full_title: {ko: 'Classical Mechanics, 3rd edition — Goldstein, Poole & Safko', en: 'Classical Mechanics, 3rd edition — Goldstein, Poole & Safko'},
    short_title: 'GOLDSTEIN',
    author: 'Herbert Goldstein · Charles P. Poole · John L. Safko',
    topic_label: {ko: '고전역학', en: 'Classical mechanics'},
    collection: 'physics',
    href: 'https://www.pearson.com/en-us/subject-catalog/p/Goldstein-Classical-Mechanics-3rd-Edition/P200000006871?view=educator',
    availability: 'digitization_pending',
    resource_kind: 'textbook'
  },
  {
    id: 'kzhou-handouts',
    title: {ko: 'Physics Olympiad Handouts Kevin Zhou', en: 'Physics Olympiad Handouts Kevin Zhou'},
    full_title: {ko: 'Physics Olympiad Handouts — Kevin Zhou', en: 'Physics Olympiad Handouts — Kevin Zhou'},
    short_title: 'KZHOU',
    author: 'Kevin Zhou',
    topic_label: {ko: '물리올림피아드', en: 'Physics Olympiad'},
    collection: 'physics',
    href: 'https://knzhou.github.io/teaching/',
    availability: 'official_online',
    resource_kind: 'handouts'
  },
  {
    id: 'feynman-1',
    title: {ko: 'The Feynman Lectures on Physics, Vol. I', en: 'The Feynman Lectures on Physics, Vol. I'},
    full_title: {ko: 'The Feynman Lectures on Physics, Volume I — Feynman, Leighton & Sands', en: 'The Feynman Lectures on Physics, Volume I — Feynman, Leighton & Sands'},
    short_title: 'FEYNMAN I',
    author: 'Richard P. Feynman · Robert B. Leighton · Matthew Sands',
    topic_label: {ko: '역학 · 복사 · 열', en: 'Mechanics, radiation and heat'},
    collection: 'physics',
    href: 'https://www.feynmanlectures.caltech.edu/I_toc.html',
    availability: 'official_online',
    resource_kind: 'lectures'
  },
  {
    id: 'feynman-2',
    title: {ko: 'The Feynman Lectures on Physics, Vol. II', en: 'The Feynman Lectures on Physics, Vol. II'},
    full_title: {ko: 'The Feynman Lectures on Physics, Volume II — Feynman, Leighton & Sands', en: 'The Feynman Lectures on Physics, Volume II — Feynman, Leighton & Sands'},
    short_title: 'FEYNMAN II',
    author: 'Richard P. Feynman · Robert B. Leighton · Matthew Sands',
    topic_label: {ko: '전자기학 · 물질', en: 'Electromagnetism and matter'},
    collection: 'physics',
    href: 'https://www.feynmanlectures.caltech.edu/II_toc.html',
    availability: 'official_online',
    resource_kind: 'lectures'
  },
  {
    id: 'feynman-3',
    title: {ko: 'The Feynman Lectures on Physics, Vol. III', en: 'The Feynman Lectures on Physics, Vol. III'},
    full_title: {ko: 'The Feynman Lectures on Physics, Volume III — Feynman, Leighton & Sands', en: 'The Feynman Lectures on Physics, Volume III — Feynman, Leighton & Sands'},
    short_title: 'FEYNMAN III',
    author: 'Richard P. Feynman · Robert B. Leighton · Matthew Sands',
    topic_label: {ko: '양자역학', en: 'Quantum mechanics'},
    collection: 'physics',
    href: 'https://www.feynmanlectures.caltech.edu/III_toc.html',
    availability: 'official_online',
    resource_kind: 'lectures'
  }
].map(item => Object.freeze({...item, title: Object.freeze(item.title), full_title: Object.freeze(item.full_title), topic_label: Object.freeze(item.topic_label)})));
