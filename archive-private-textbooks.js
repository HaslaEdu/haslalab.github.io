import {FEYNMAN_EXERCISES, FEYNMAN_TOPICS} from './feynman-exercises.js?v=96ba74fa5757';

const API = '/api/problem-bank/private-textbooks';
const BOOK = /^[a-z][a-z0-9-]{0,31}$/;
const WEBP = /^image\/webp(?:;|$)/i;
const PDF = /^application\/pdf(?:;|$)/i;
const FEYNMAN_SITE = 'https://www.feynmanlectures.caltech.edu/';
const FEYNMAN_WORKBOOK = API + '/books/feynman/workbook';
const PUBLIC_FEYNMAN = {
  id: 'feynman',
  title: 'The Feynman Lectures on Physics',
  volumes: [
    {number: 1, title: 'Mainly Mechanics, Radiation, and Heat', toc: 'I_toc.html'},
    {number: 2, title: 'Mainly Electromagnetism and Matter', toc: 'II_toc.html'},
    {number: 3, title: 'Quantum Mechanics', toc: 'III_toc.html'},
  ],
};
const COPY = {
  ko: {
    heading: '내 비공개 교재', home: '← 교재 아카이브', loading: '자료를 불러오는 중…',
    login: '로그인', loginNeeded: '교재를 보려면 승인된 계정으로 로그인하세요.',
    denied: '이 계정에는 비공개 교재 열람 권한이 없습니다.',
    failed: '교재를 열지 못했습니다.', retry: '다시 시도', book: '교재', allBooks: '교재를 선택하세요',
    count: '문제', koreanCount: '한국어', find: '문제 번호 또는 장 이름', search: '찾기',
    empty: '검색 결과가 없습니다.', contents: '목차', pageContents: '현재 페이지 목차', allProblems: '전체 문항', unchaptered: '장 미분류', previous: '이전', next: '다음', back: '← 문제 목록',
    question: '문제', noKorean: '이 문제의 한국어 본문은 준비 중입니다.',
    original: '원문 이미지', showImage: '이미지 보기', imageError: '이미지를 불러오지 못했습니다.',
    question_crop: '문제 원문', source_page: '원본 PDF', english_page: '영어 참고판', figure: '문제 그림',
    page: '쪽', source_compared: '원문 대조', model_source_reviewed: 'AI 원문 대조',
    machine_draft: '자동 번역 초안', upstream_corrected_edition: '원본 사이트 영어판',
    pending: '원문 대조 필요', source_scan: '원본 스캔 · 본문은 이미지에서 확인', source_extracted: '영어 원문 추출', study_adapted: '한국어 학습용 순화판', structured_english_russian: '공개 영어·러시아어 본문 기준',
    volume: '권 선택', findChapter: '장 번호 또는 제목', noChapters: '일치하는 장이 없습니다.',
    chapterCount: '개 장', supplement: '부록', openPdf: '원본 PDF 열기', newTabPdf: '새 탭에서 PDF 열기',
    pdfError: 'PDF를 불러오지 못했습니다.', exercises: '연습문제',
    exerciseTitle: 'Caltech 공개 연습문제', findExercise: '연습문제 검색',
    exerciseNote: '문항별 영어 요약입니다. 문제의 전체 조건, 그림과 해설은 각 문항의 Caltech 원문에서 볼 수 있습니다.',
    exerciseSource: 'Caltech 원문 열기', exerciseIndex: 'Caltech 전체 목록', chapterReference: '강의 본문',
    workbook: '파인만 별책 연습문제집', workbookContents: '목차', workbookAnswers: '정답·해설',
    workbookSearch: '문항 번호 또는 장 제목', workbookOriginal: '영어 원본 스캔',
    workbookKorean: '한국어 문항', workbookDraft: '스캔 OCR을 바탕으로 한 번역 초안입니다. 수식·그림은 영어 원본에서 확인하세요.',
    onlineEdition: 'Caltech 공식 온라인판 열기', lectureLogin: 'Drive 원본 PDF는 승인된 계정으로 열 수 있습니다.',
  },
  en: {
    heading: 'My private textbooks', home: '← Book archive', loading: 'Loading…',
    login: 'Sign in', loginNeeded: 'Sign in with an approved account to view the textbooks.',
    denied: 'Your account does not have access to the private textbooks.',
    failed: 'Could not open the textbooks.', retry: 'Retry', book: 'Book', allBooks: 'Choose a book',
    count: 'problems', koreanCount: 'Korean', find: 'Problem number or chapter', search: 'Find',
    empty: 'No matching problems.', contents: 'Contents', pageContents: 'Contents on this page', allProblems: 'All problems', unchaptered: 'Unassigned', previous: 'Previous', next: 'Next', back: '← Problem list',
    question: 'Problem', noKorean: 'A Korean statement is still being prepared for this problem.',
    original: 'Original image', showImage: 'Show image', imageError: 'Could not load the image.',
    question_crop: 'Problem excerpt', source_page: 'Original PDF', english_page: 'English reference edition',
    figure: 'Problem diagram', page: 'p.', source_compared: 'Compared with source',
    model_source_reviewed: 'AI comparison with source', machine_draft: 'Machine translation draft',
    upstream_corrected_edition: 'English edition from the source website', pending: 'Source comparison pending', source_scan: 'Source scan · read the original image', source_extracted: 'Extracted English text', study_adapted: 'Korean study adaptation',
    structured_english_russian: 'Based on the published English and Russian statements',
    volume: 'Choose a volume', findChapter: 'Chapter number or title', noChapters: 'No matching chapters.',
    chapterCount: 'chapters', supplement: 'Appendix', openPdf: 'Open original PDF', newTabPdf: 'Open PDF in a new tab',
    pdfError: 'Could not load the PDF.', exercises: 'Exercises',
    exerciseTitle: 'Caltech’s public exercises', findExercise: 'Find an exercise',
    exerciseNote: 'Short English summaries. Open each Caltech original for the full statement, diagrams and solutions.',
    exerciseSource: 'Open Caltech original', exerciseIndex: 'Caltech’s full index', chapterReference: 'Lecture reference',
    workbook: 'Exercises for the Feynman Lectures on Physics', workbookContents: 'Contents', workbookAnswers: 'Answers and solutions',
    workbookSearch: 'Problem number or chapter title', workbookOriginal: 'Original English scan',
    workbookKorean: 'Korean exercises', workbookDraft: 'Draft translated from scan OCR. Check the English scan for equations and figures.',
    onlineEdition: 'Open the official Caltech edition', lectureLogin: 'Sign in with an approved account to open the Drive PDFs.',
  },
};

export function textbookStatement(record, language) {
  const item = language === 'ko' ? record.ko : record.en;
  return typeof item?.text === 'string' && item.text ? item : null;
}

export function mountPrivateTextbooks(container, options) {
  const doc = container.ownerDocument;
  const win = doc.defaultView;
  const words = COPY[options.lang === 'en' ? 'en' : 'ko'];
  const origin = new URL(options.apiOrigin).origin;
  const atom = (tag, value = '') => {
    const node = doc.createElement(tag);
    node.textContent = value;
    return node;
  };
  const root = atom('section');
  root.className = 'al al-private-textbooks';
  root.dataset.theme = options.theme;
  const header = atom('header');
  const title = atom('h2', words.heading);
  const home = atom('a', words.home);
  home.href = '#/archive/books/phys';
  header.append(title, home);
  const content = atom('div');
  const notice = atom('p');
  notice.setAttribute('role', 'status');
  notice.className = 'al-status';
  root.append(header, notice, content);
  container.replaceChildren(root);

  const token = () => String(options.getToken?.() || '');
  let observedToken = token();
  const requestedBook = options.params?.get('book') || '';
  const bookState = book => ({book, page: 1, q: '', problem: null, volume: null, chapter: null});
  const initialState = () => ({
    ...bookState(BOOK.test(requestedBook) ? requestedBook : ''),
    volume: requestedBook === 'feynman' && options.params?.get('section') === 'exercises' ? 'exercises' : null,
  });
  let state = initialState();
  let books = [];
  let disposed = false;
  let epoch = 0;
  let imageUrl;
  let pending;
  function button(label, click) {
    const element = atom('button', label);
    element.type = 'button';
    element.addEventListener('click', click);
    return element;
  }
  function groupProblems(items, chapterOf) {
    const groups = new Map();
    for (const item of items) {
      const chapter = chapterOf(item);
      if (!groups.has(chapter)) groups.set(chapter, []);
      groups.get(chapter).push(item);
    }
    return groups;
  }

  function chapterBrowser(indexTitle, renderRows, onChange = () => {}) {
    const element = atom('div');
    element.className = 'al-source-layout al-private-chapters';
    const outline = atom('aside');
    outline.className = 'al-toc';
    const nav = atom('nav');
    nav.setAttribute('aria-label', indexTitle);
    const main = atom('section');
    main.className = 'al-source-main';
    const result = atom('div');
    main.append(result);
    element.append(outline, main);
    function update(groups, active) {
      const list = atom('ol');
      const heading = atom('h3', indexTitle);
      nav.replaceChildren(heading, list);
      outline.replaceChildren(nav);
      outline.hidden = !groups.size;
      element.classList.toggle('is-flat', !groups.size);
      const all = [...groups.values()].flat();
      const currentChapter = groups.has(active) ? active : groups.size === 1 ? groups.keys().next().value : null;
      const entries = [...groups];
      const rows = currentChapter === null ? all : groups.get(currentChapter);
      if (entries.length > 1) entries.unshift([null, all]);
      for (const [chapter, items] of entries) {
        const item = atom('li');
        const choice = button(chapter ?? words.allProblems, () => {
          onChange(chapter);
          update(groups, chapter);
          nav.querySelector('[aria-current="true"]')?.focus({preventScroll: true});
        });
        choice.append(atom('small', String(items.length)));
        if (chapter === currentChapter) choice.setAttribute('aria-current', 'true');
        item.append(choice);
        list.append(item);
      }
      result.replaceChildren(rows.length ? renderRows(rows) : atom('p', words.empty));
    }
    return {element, main, update};
  }

  function release() {
    if (!imageUrl) return;
    win.URL.revokeObjectURL(imageUrl);
    imageUrl = null;
  }
  function invalidate() {
    pending?.abort();
    release();
    return ++epoch;
  }
  const current = run => !disposed && epoch === run && token() === observedToken;

  async function get(path, run, mediaType = null) {
    const url = new URL(path, origin);
    if (url.origin !== origin || !url.pathname.startsWith(API + '/books')) throw Error('invalid_url');
    pending?.abort();
    const controller = new win.AbortController();
    pending = controller;
    const response = await win.fetch(url, {
      headers: {Authorization: 'Bearer ' + observedToken}, credentials: 'omit',
      cache: 'no-store', redirect: 'error', signal: controller.signal,
    });
    if (!response.ok) throw Object.assign(Error('archive_failed'), {status: response.status});
    const data = mediaType ? await response.blob() : await response.json();
    if (mediaType && !mediaType.test(data.type)) throw Error('invalid_media');
    if (!current(run) || controller.signal.aborted) throw new win.DOMException('Stale response', 'AbortError');
    return data;
  }

  function showFailure(error) {
    if (error?.name === 'AbortError') return;
    const label = error?.status === 401 ? words.loginNeeded :
      error?.status === 403 ? words.denied : words.failed;
    notice.textContent = label;
    content.replaceChildren();
    if (error?.status === 401) content.append(button(words.login, () => options.onLogin?.()));
    else if (error?.status !== 403) content.append(button(words.retry, refresh));
  }

  function bookPicker() {
    const label = atom('label', words.book + ' ');
    const select = atom('select');
    const choice = atom('option', words.allBooks);
    choice.value = '';
    select.append(choice);
    for (const book of books) {
      if (!BOOK.test(book.id)) continue;
      const option = atom('option', book.title);
      option.value = book.id;
      select.append(option);
    }
    select.value = state.book;
    select.addEventListener('change', () => {
      state = bookState(select.value);
      refresh();
    });
    label.append(select);
    return label;
  }

  function renderBooks() {
    const list = atom('ul');
    list.className = 'al-private-book-list';
    for (const book of books) {
      if (!BOOK.test(book.id)) continue;
      const item = atom('li');
      item.append(button(book.title, () => {
        state = bookState(book.id);
        refresh();
      }), atom('small', book.kind === 'lectures' ? book.count + ' ' + words.chapterCount :
        book.count + ' ' + words.count + ' · ' + words.koreanCount + ' ' + book.korean_count));
      list.append(item);
    }
    content.replaceChildren(list);
  }

  function renderLectures(book, volume, run) {
    const publicEdition = book === PUBLIC_FEYNMAN;
    title.textContent = book.title;
    const choices = atom('nav');
    choices.className = 'al-private-controls';
    choices.setAttribute('aria-label', words.volume);
    function addChoice(label, value) {
      const choice = button(label, async () => {
        if (state.volume === value) return;
        state.volume = value;
        await refresh();
        if (!disposed && state.book === book.id && state.volume === value) {
          content.querySelector('nav button[aria-pressed="true"]')?.focus({preventScroll: true});
        }
      });
      choice.setAttribute('aria-pressed', String(state.volume === value));
      choices.append(choice);
    }
    for (const item of book.volumes) addChoice('Volume ' + item.number, item.number);
    addChoice(words.exercises, 'exercises');
    content.replaceChildren(...(publicEdition ? [] : [bookPicker()]), choices);
    if (state.volume === 'exercises') {
      const workbook = atom('section');
      workbook.className = 'al-feynman-workbook';
      content.append(workbook, renderExerciseIndex());
      if (publicEdition) {
        workbook.append(atom('h3', words.workbook), atom('p', words.lectureLogin));
        if (!observedToken) workbook.append(button(words.login, () => options.onLogin?.()));
      } else {
        void loadWorkbook(workbook, run);
      }
      return;
    }
    if (publicEdition) {
      content.append(atom('p', words.lectureLogin));
      if (!observedToken) content.append(button(words.login, () => options.onLogin?.()));
    }
    if (!volume) return;

    const volumeTitle = atom('h3', 'Volume ' + volume.number + ' · ' + volume.title);
    const official = atom('a', words.onlineEdition);
    official.href = FEYNMAN_SITE + PUBLIC_FEYNMAN.volumes[volume.number - 1].toc;
    official.target = '_blank';
    official.rel = 'noopener noreferrer';
    const links = atom('div');
    links.className = 'al-private-controls';
    links.append(official);
    if (publicEdition) {
      content.append(volumeTitle, links);
      return;
    }
    const preview = atom('section');
    const previewStatus = atom('p');
    previewStatus.setAttribute('role', 'status');
    const open = atom('a', words.newTabPdf);
    open.target = '_blank';
    open.rel = 'noopener';
    const frame = atom('iframe');
    frame.title = volumeTitle.textContent;
    frame.className = 'al-private-pdf';
    preview.append(previewStatus, open, frame);
    open.hidden = frame.hidden = true;
    async function showPdf(page) {
      previewStatus.textContent = words.loading;
      try {
        if (!imageUrl) {
          const pdfBlob = await get(API + '/books/' + book.id + '/volumes/' + volume.number + '/pdf', run, PDF);
          imageUrl = win.URL.createObjectURL(pdfBlob);
        }
        const pageUrl = imageUrl + '#page=' + page;
        open.href = pageUrl;
        frame.src = pageUrl;
        open.hidden = frame.hidden = false;
        previewStatus.textContent = '';
        preview.scrollIntoView({block: 'start'});
      } catch (error) {
        if (current(run) && error.name !== 'AbortError') previewStatus.textContent = words.pdfError;
      }
    }
    const controls = atom('div');
    controls.className = 'al-private-controls';
    const find = atom('label', words.findChapter + ' ');
    const search = atom('input');
    search.type = 'search';
    search.maxLength = 160;
    find.append(search);
    controls.append(find, button(words.openPdf, () => showPdf(1)));
    const chapters = atom('ul');
    chapters.className = 'al-private-book-list';
    const empty = atom('p', words.noChapters);
    function filterChapters() {
      const query = search.value.trim().normalize('NFKC').toLowerCase();
      const matches = volume.chapters.filter(chapter => String(chapter.number) === query ||
        chapter.title.normalize('NFKC').toLowerCase().includes(query));
      chapters.replaceChildren(...matches.map(chapter => {
        const item = atom('li');
        const title = (chapter.supplement ? words.supplement + ' · ' : '') + chapter.number + '. ' + chapter.title;
        item.append(button(title, () => showPdf(chapter.page)), atom('small', words.page + ' ' + chapter.page));
        return item;
      }));
      empty.hidden = matches.length > 0;
    }
    search.addEventListener('input', filterChapters);
    filterChapters();
    content.append(volumeTitle, preview, controls, chapters, empty, links);
  }

  async function loadWorkbook(section, run) {
    section.append(atom('h3', words.workbook));
    const status = atom('p', words.loading);
    status.setAttribute('role', 'status');
    section.append(status);
    let workbook;
    try {
      workbook = await get(FEYNMAN_WORKBOOK, run);
    } catch (error) {
      if (current(run) && error.name !== 'AbortError') status.textContent = words.failed;
      return;
    }
    status.textContent = workbook.count + ' ' + words.count + ' · ' + (workbook.korean_count > 0
      ? words.workbookKorean + ' ' + workbook.korean_count : words.workbookOriginal);
    const controls = atom('div');
    controls.className = 'al-private-controls';
    const volumeLabel = atom('label', words.volume + ' ');
    const volume = atom('select');
    for (const [number, label] of ['I', 'II', 'III'].entries()) {
      const option = atom('option', 'Volume ' + label);
      option.value = String(number + 1);
      volume.append(option);
    }
    volumeLabel.append(volume);
    const searchLabel = atom('label', words.workbookSearch + ' ');
    const search = atom('input');
    search.type = 'search';
    search.maxLength = 160;
    searchLabel.append(search);
    const preview = atom('section');
    const problemHeader = atom('h4');
    const languages = atom('div');
    languages.className = 'al-private-controls';
    const translation = atom('section');
    const translationStatus = atom('p');
    translationStatus.className = 'al-muted';
    const translationBody = atom('div');
    translationBody.lang = 'ko';
    translationBody.className = 'al-prose';
    translationBody.style.whiteSpace = 'pre-wrap';
    translation.append(translationStatus, translationBody);
    const previewStatus = atom('p');
    previewStatus.setAttribute('role', 'status');
    const open = atom('a', words.newTabPdf);
    open.target = '_blank';
    open.rel = 'noopener';
    const frame = atom('iframe');
    frame.className = 'al-private-pdf';
    frame.title = words.workbook;
    open.hidden = frame.hidden = true;
    const pageControls = atom('div');
    pageControls.className = 'al-private-controls';
    const previousPart = button(words.previous, () => showPage(workbook.parts[loadedPart - 1].end));
    const nextPart = button(words.next, () => showPage(workbook.parts[loadedPart + 1].start));
    previousPart.hidden = nextPart.hidden = true;
    pageControls.append(previousPart, nextPart, open);
    const original = atom('div');
    original.append(previewStatus, pageControls, frame);
    preview.append(problemHeader, languages, translation, original);
    translation.hidden = true;
    let loadedPart = -1;
    let selected = null;
    let selection = 0;
    const ko = button('한국어', () => selectLanguage('ko'));
    const en = button('English', () => selectLanguage('en'));
    languages.append(ko, en);
    languages.hidden = true;
    function selectLanguage(language) {
      if (!selected) return;
      const useKorean = language === 'ko' && selected.ko;
      ko.setAttribute('aria-pressed', String(Boolean(useKorean)));
      en.setAttribute('aria-pressed', String(!useKorean));
      translation.hidden = !useKorean;
      original.hidden = Boolean(useKorean);
      if (!useKorean) {
        void showPage(selected.page);
        return;
      }
      pending?.abort();
      translationStatus.textContent = selected.ko.review_status === 'source_compared'
        ? words.source_compared : words.workbookDraft;
      translationBody.textContent = selected.ko.text;
      Promise.resolve(options.renderMath?.(translationBody)).catch(() => {});
      preview.scrollIntoView({block: 'start'});
    }
    async function openProblem(number, page) {
      const attempt = ++selection;
      pending?.abort();
      selected = null;
      translation.hidden = languages.hidden = true;
      original.hidden = false;
      frame.hidden = open.hidden = previousPart.hidden = nextPart.hidden = true;
      problemHeader.textContent = words.question + ' ' + number;
      previewStatus.textContent = words.loading;
      let row;
      if (workbook.korean_count > 0) {
        try {
          row = await get(FEYNMAN_WORKBOOK + '/questions/' + number, run);
        } catch (error) {
          if (error.name === 'AbortError' || !current(run)) return;
        }
      }
      if (attempt !== selection || !current(run)) return;
      selected = {page, ko: row?.ko};
      languages.hidden = !selected.ko;
      selectLanguage('en');
    }
    function openReference(page) {
      selection++;
      pending?.abort();
      selected = null;
      problemHeader.textContent = '';
      languages.hidden = translation.hidden = true;
      original.hidden = false;
      void showPage(page);
    }
    async function showPage(page) {
      const part = workbook.parts.findIndex(row => row.start <= page && page <= row.end);
      if (part < 0 || !current(run)) return;
      previewStatus.textContent = words.loading;
      try {
        if (part !== loadedPart || !imageUrl) {
          release();
          loadedPart = -1;
          previousPart.hidden = nextPart.hidden = open.hidden = frame.hidden = true;
          const pdf = await get(FEYNMAN_WORKBOOK + '/parts/' + (part + 1), run, PDF);
          imageUrl = win.URL.createObjectURL(pdf);
          loadedPart = part;
        } else {
          pending?.abort();
        }
        const pageUrl = imageUrl + '#page=' + (page - workbook.parts[part].start + 1);
        open.href = pageUrl;
        frame.src = pageUrl;
        open.hidden = frame.hidden = false;
        previousPart.hidden = part === 0;
        nextPart.hidden = part === workbook.parts.length - 1;
        previewStatus.textContent = words.page + ' ' + page;
        preview.scrollIntoView({block: 'start'});
      } catch (error) {
        if (current(run) && error.name !== 'AbortError') previewStatus.textContent = words.pdfError;
      }
    }
    let activeChapter = null;
    const chapters = chapterBrowser(words.contents, rows => {
      const list = atom('ul');
      list.className = 'al-private-book-list';
      for (const [number, page, chapter] of rows) {
        const item = atom('li');
        item.append(button(number, () => openProblem(number, page)), atom('small', chapter));
        list.append(item);
      }
      return list;
    }, chapter => { activeChapter = chapter; });
    function renderChapters() {
      const query = search.value.trim().normalize('NFKC').toLowerCase();
      const matches = [];
      for (const chapter of workbook.chapters) {
        if (!query && chapter.volume !== Number(volume.value)) continue;
        const wholeChapter = !query || String(chapter.number) === query ||
          chapter.title.normalize('NFKC').toLowerCase().includes(query);
        const label = chapter.number + '. ' + chapter.title;
        chapter.problems.forEach((page, offset) => {
          const number = chapter.number + '.' + (offset + 1);
          if (wholeChapter || number === query) matches.push([number, page, label]);
        });
      }
      chapters.update(groupProblems(matches, row => row[2]), activeChapter);
    }
    volume.addEventListener('change', () => { search.value = ''; activeChapter = null; renderChapters(); });
    search.addEventListener('input', () => { activeChapter = null; renderChapters(); });
    controls.append(volumeLabel, searchLabel, button(words.workbookContents, () => openReference(workbook.contents)),
      button(words.workbookAnswers, () => openReference(workbook.answers)));
    renderChapters();
    chapters.main.append(preview);
    section.append(controls, chapters.element);
  }

  function renderExerciseIndex() {
    const section = atom('section');
    section.className = 'al-feynman-exercises';
    const title = atom('h3', words.exerciseTitle);
    const controls = atom('div');
    controls.className = 'al-private-controls';
    const label = atom('label', words.findExercise + ' ');
    const search = atom('input');
    search.type = 'search';
    search.maxLength = 160;
    label.append(search);
    const count = atom('p');
    count.className = 'al-muted';
    count.setAttribute('role', 'status');
    controls.append(label);
    let activeTopic = null;
    const topicsBySlug = new Map(FEYNMAN_TOPICS.flatMap(([topic, ...slugs]) => slugs.map(slug => [slug, topic])));
    const chapters = chapterBrowser(words.contents, rows => {
      const results = atom('div');
      for (const [slug, , titleEn, , summaryEn, chapter] of rows) {
        const row = atom('details');
        row.dataset.source = slug;
        row.lang = 'en';
        row.append(atom('summary', titleEn), atom('p', summaryEn));
        if (chapter) row.append(atom('p', words.chapterReference + ' ' + chapter));
        const source = atom('a', words.exerciseSource);
        source.href = FEYNMAN_SITE + 'info/exercises/' + slug + '.html';
        source.target = '_blank';
        source.rel = 'noopener noreferrer';
        row.append(source);
        results.append(row);
      }
      return results;
    }, topic => { activeTopic = topic; });
    const normalize = value => value.normalize('NFKC').toLowerCase();
    function renderRows() {
      const query = normalize(search.value.trim());
      const matches = FEYNMAN_EXERCISES.filter(row => !query ||
        normalize([...row.slice(1), topicsBySlug.get(row[0]) || ''].join(' ')).includes(query));
      count.textContent = matches.length ? matches.length + ' ' + words.count : words.empty;
      chapters.update(groupProblems(matches, row => topicsBySlug.get(row[0]) || words.unchaptered), activeTopic);
    }
    search.addEventListener('input', () => { activeTopic = null; renderRows(); });
    const index = atom('a', words.exerciseIndex);
    index.href = FEYNMAN_SITE + 'info/exercises.html';
    index.target = '_blank';
    index.rel = 'noopener noreferrer';
    renderRows();
    section.append(title, atom('p', words.exerciseNote), controls, count, chapters.element, index);
    return section;
  }

  function showPublicLectures(run) {
    renderLectures(PUBLIC_FEYNMAN, PUBLIC_FEYNMAN.volumes.find(volume => volume.number === state.volume), run);
    notice.textContent = '';
  }

  function renderList(data) {
    const form = atom('form');
    form.className = 'al-private-controls';
    const label = atom('label', words.find + ' ');
    const input = atom('input');
    input.type = 'search';
    input.maxLength = 160;
    input.value = state.q;
    label.append(input);
    const submit = atom('button', words.search);
    form.append(label, submit);
    form.addEventListener('submit', event => {
      event.preventDefault();
      state.q = input.value.trim();
      state.page = 1;
      state.chapter = null;
      refresh();
    });
    const chapterOf = item => item.chapter?.trim() || words.unchaptered;
    const chapters = chapterBrowser(data.pages > 1 ? words.pageContents : words.contents, items => {
      const rows = atom('ul');
      rows.className = 'al-private-book-list';
      for (const item of items) {
        const entry = atom('li');
        const label = [item.number, item.label].filter(Boolean).join(' · ');
        entry.append(button(label, () => {
          state.problem = item.ordinal;
          refresh();
        }), atom('small', [chapterOf(item), item.has_korean ? (item.has_english === false ? 'KO' : 'KO · EN') : 'EN'].join(' · ')));
        rows.append(entry);
      }
      return rows;
    }, chapter => { state.chapter = chapter; });
    chapters.update(groupProblems(data.items, chapterOf), state.chapter);
    const counts = atom('p', data.total + ' ' + words.count);
    counts.className = 'al-muted';
    const pages = atom('nav');
    pages.className = 'al-private-controls';
    const jump = n => { state.page = n; state.chapter = null; refresh(); };
    const previous = button(words.previous, () => jump(state.page - 1));
    previous.disabled = state.page <= 1;
    const next = button(words.next, () => jump(state.page + 1));
    next.disabled = state.page >= data.pages;
    pages.append(previous, atom('span', data.page + ' / ' + data.pages), next);
    content.replaceChildren(bookPicker(), form, counts, chapters.element, pages);
  }

  function renderQuestion(row, run) {
    const reader = atom('article');
    reader.className = 'al-reader';
    const back = button(words.back, () => { state.problem = null; refresh(); });
    const tools = atom('div');
    tools.className = 'al-private-controls';
    const ko = button('한국어', () => selectLanguage('ko'));
    const en = button('English', () => selectLanguage('en'));
    if (row.ko) tools.append(ko);
    if (row.en) tools.append(en);
    const label = atom('h3', [words.question + ' ' + row.number, row.label].filter(Boolean).join(' · '));
    const note = atom('p');
    note.className = 'al-muted';
    const prose = atom('div');
    prose.className = 'al-prose al-private-prose';
    function selectLanguage(language) {
      const body = textbookStatement(row, language);
      ko.setAttribute('aria-pressed', String(language === 'ko'));
      en.setAttribute('aria-pressed', String(language === 'en'));
      prose.lang = language;
      prose.textContent = body?.text ?? words.noKorean;
      note.textContent = body ? [words[body.review_status] || words.pending,
                                 words[body.review_basis]].filter(Boolean).join(' · ') : '';
      if (body) Promise.resolve(options.renderMath?.(prose)).catch(() => {});
    }
    const meta = atom('p', [row.book.title, row.chapter].filter(Boolean).join(' · '));
    meta.className = 'al-meta';
    reader.append(back, meta, label, tools, note, prose);
    if (/^https:\/\/savchenkosolutions\.com\/en\/[0-9]+(?:\.[0-9]+){2}$/.test(row.credit?.source_url)) {
      const credit = atom('p');
      credit.className = 'al-meta';
      const source = atom('a', 'Savchenko Solutions');
      source.href = row.credit.source_url;
      const license = atom('a', 'CC BY-SA 4.0');
      license.href = 'https://creativecommons.org/licenses/by-sa/4.0/';
      credit.append(source, license);
      reader.append(credit);
    }
    const images = row.media || [];
    let loadSourceScan;
    if (images.length) {
      const section = atom('section');
      const chooser = atom('div');
      chooser.className = 'al-private-controls';
      const mediaLabel = atom('label', words.original + ' ');
      const select = atom('select');
      const stage = atom('div');
      stage.className = 'al-figures';
      for (const item of images) {
        const description = [words[item.kind] ?? words.original,
                             item.page ? words.page + ' ' + item.page : '', item.label]
          .filter(Boolean).join(' · ');
        const option = atom('option', description);
        option.value = String(item.id);
        select.append(option);
      }
      const loadImage = async () => {
        const item = images.find(i => String(i.id) === select.value);
        if (!item || !current(run)) return;
        const exact = API + '/books/' + state.book + '/questions/' + row.ordinal + '/media/' + item.id;
        if (item.url !== exact) return;
        show.disabled = true;
        release();
        stage.replaceChildren(atom('p', words.loading));
        try {
          const data = await get(exact, run, WEBP);
          imageUrl = win.URL.createObjectURL(data);
          const img = atom('img');
          const caption = select.options[select.selectedIndex].textContent;
          img.alt = caption;
          img.src = imageUrl;
          const figure = atom('figure');
          figure.append(img, atom('figcaption', caption));
          stage.replaceChildren(figure);
        } catch (error) {
          if (current(run) && error.name !== 'AbortError') stage.replaceChildren(atom('p', words.imageError));
        } finally {
          show.disabled = false;
        }
      };
      const show = button(words.showImage, loadImage);
      if (row.ko?.review_status === 'source_scan') loadSourceScan = loadImage;
      select.addEventListener('change', () => {
        pending?.abort();
        release();
        stage.replaceChildren();
      });
      mediaLabel.append(select);
      chooser.append(mediaLabel, show);
      section.append(chooser, stage);
      reader.append(section);
    }
    content.replaceChildren(reader);
    const initial = row.ko && (!row.en || options.lang !== 'en') ? 'ko' : 'en';
    selectLanguage(initial);
    if (loadSourceScan) void loadSourceScan();
  }

  async function refresh() {
    if (disposed) return;
    const run = invalidate();
    title.textContent = words.heading;
    content.replaceChildren();
    notice.textContent = words.loading;
    if (!observedToken) {
      if (state.book === 'feynman') showPublicLectures(run);
      else showFailure({status: 401});
      return;
    }
    try {
      if (!books.length) books = (await get(API + '/books', run)).books;
      const book = books.find(book => book.id === state.book);
      if (!book) {
        if (state.book === 'feynman') {
          showPublicLectures(run);
          return;
        }
        state = bookState('');
        renderBooks();
      } else if (book.kind === 'lectures') {
        const volume = Number.isInteger(state.volume) ? await get(API + '/books/' + book.id + '/volumes/' + state.volume, run) : null;
        renderLectures(book, volume, run);
      } else if (state.problem) {
        const row = await get(API + '/books/' + state.book + '/questions/' + state.problem, run);
        renderQuestion(row, run);
      } else {
        const query = new URLSearchParams({page: String(state.page)});
        if (state.q) query.set('q', state.q);
        renderList(await get(API + '/books/' + state.book + '?' + query, run));
      }
      notice.textContent = '';
    } catch (error) {
      if (!current(run)) return;
      if (state.book === 'feynman' && (state.volume === 'exercises' || error.status === 401 || error.status === 403)) showPublicLectures(run);
      else showFailure(error);
    }
  }

  function authChanged() {
    const next = token();
    if (next === observedToken || disposed) return;
    observedToken = next;
    books = [];
    state = initialState();
    refresh();
  }
  win.addEventListener('storage', authChanged);
  refresh();
  return {
    update(next) {
      if (next.theme) root.dataset.theme = next.theme;
      authChanged();
    },
    dispose() {
      disposed = true;
      invalidate();
      win.removeEventListener('storage', authChanged);
      root.remove();
    },
  };
}
