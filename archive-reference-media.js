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
    id: 'feynman',
    title: {ko: 'The Feynman Lectures on Physics', en: 'The Feynman Lectures on Physics'},
    full_title: {ko: 'The Feynman Lectures on Physics', en: 'The Feynman Lectures on Physics'},
    short_title: 'Feynman',
    author: 'Richard P. Feynman · Robert B. Leighton · Matthew Sands',
    topic_label: {ko: '역학 · 전자기학 · 양자역학', en: 'Mechanics, electromagnetism and quantum mechanics'},
    collection: 'physics',
    href: 'https://www.feynmanlectures.caltech.edu/',
    availability: 'official_online',
    resource_kind: 'lectures'
  }
].map(item => Object.freeze({...item, title: Object.freeze(item.title), full_title: Object.freeze(item.full_title), topic_label: Object.freeze(item.topic_label)})));
