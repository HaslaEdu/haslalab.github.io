const API = '/api/problem-bank/private-textbooks';
const BOOK = /^[a-z][a-z0-9-]{0,31}$/;
const WEBP = /^image\/webp(?:;|$)/i;
const PDF = /^application\/pdf(?:;|$)/i;
const FEYNMAN_SITE = 'https://www.feynmanlectures.caltech.edu/';
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
    empty: '검색 결과가 없습니다.', previous: '이전', next: '다음', back: '← 문제 목록',
    question: '문제', noKorean: '이 문제의 한국어 본문은 준비 중입니다.',
    original: '원문 이미지', showImage: '이미지 보기', imageError: '이미지를 불러오지 못했습니다.',
    question_crop: '문제 원문', source_page: '원본 PDF', english_page: '영어 참고판', figure: '문제 그림',
    page: '쪽', source_compared: '원문 대조', model_source_reviewed: 'AI 원문 대조',
    machine_draft: '자동 번역 초안', upstream_corrected_edition: '원본 사이트 영어판',
    pending: '원문 대조 필요', source_scan: '원본 스캔 · 본문은 이미지에서 확인', source_extracted: '영어 원문 추출', study_adapted: '한국어 학습용 순화판', structured_english_russian: '공개 영어·러시아어 본문 기준',
    volume: '권 선택', findChapter: '장 번호 또는 제목', noChapters: '일치하는 장이 없습니다.',
    chapterCount: '개 장', supplement: '부록', openPdf: '원본 PDF 열기', newTabPdf: '새 탭에서 PDF 열기',
    pdfError: 'PDF를 불러오지 못했습니다.', exercises: 'Caltech 공식 연습문제',
    onlineEdition: 'Caltech 공식 온라인판 열기', lectureLogin: 'Drive 원본 PDF는 승인된 계정으로 열 수 있습니다.',
  },
  en: {
    heading: 'My private textbooks', home: '← Book archive', loading: 'Loading…',
    login: 'Sign in', loginNeeded: 'Sign in with an approved account to view the textbooks.',
    denied: 'Your account does not have access to the private textbooks.',
    failed: 'Could not open the textbooks.', retry: 'Retry', book: 'Book', allBooks: 'Choose a book',
    count: 'problems', koreanCount: 'Korean', find: 'Problem number or chapter', search: 'Find',
    empty: 'No matching problems.', previous: 'Previous', next: 'Next', back: '← Problem list',
    question: 'Problem', noKorean: 'A Korean statement is still being prepared for this problem.',
    original: 'Original image', showImage: 'Show image', imageError: 'Could not load the image.',
    question_crop: 'Problem excerpt', source_page: 'Original PDF', english_page: 'English reference edition',
    figure: 'Problem diagram', page: 'p.', source_compared: 'Compared with source',
    model_source_reviewed: 'AI comparison with source', machine_draft: 'Machine translation draft',
    upstream_corrected_edition: 'English edition from the source website', pending: 'Source comparison pending', source_scan: 'Source scan · read the original image', source_extracted: 'Extracted English text', study_adapted: 'Korean study adaptation',
    structured_english_russian: 'Based on the published English and Russian statements',
    volume: 'Choose a volume', findChapter: 'Chapter number or title', noChapters: 'No matching chapters.',
    chapterCount: 'chapters', supplement: 'Appendix', openPdf: 'Open original PDF', newTabPdf: 'Open PDF in a new tab',
    pdfError: 'Could not load the PDF.', exercises: 'Official Caltech exercises',
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
  const bookState = book => ({book, page: 1, q: '', problem: null, volume: null});
  const initialState = () => bookState(BOOK.test(requestedBook) ? requestedBook : '');
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
    for (const item of book.volumes) {
      const choice = button('Volume ' + item.number, async () => {
        if (state.volume === item.number) return;
        state.volume = item.number;
        await refresh();
        if (!disposed && state.book === book.id && state.volume === item.number) {
          content.querySelector('nav button[aria-pressed="true"]')?.focus({preventScroll: true});
        }
      });
      choice.setAttribute('aria-pressed', String(state.volume === item.number));
      choices.append(choice);
    }
    content.replaceChildren(...(publicEdition ? [] : [bookPicker()]), choices);
    if (publicEdition) {
      content.append(atom('p', words.lectureLogin));
      if (!observedToken) content.append(button(words.login, () => options.onLogin?.()));
    }
    if (!volume) return;

    const volumeTitle = atom('h3', 'Volume ' + volume.number + ' · ' + volume.title);
    const exercises = atom('a', words.exercises);
    exercises.href = FEYNMAN_SITE + 'info/exercises.html';
    exercises.target = '_blank';
    exercises.rel = 'noopener noreferrer';
    const official = atom('a', words.onlineEdition);
    official.href = FEYNMAN_SITE + PUBLIC_FEYNMAN.volumes[volume.number - 1].toc;
    official.target = '_blank';
    official.rel = 'noopener noreferrer';
    const links = atom('div');
    links.className = 'al-private-controls';
    links.append(official, exercises);
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
      refresh();
    });
    const rows = atom('ul');
    rows.className = 'al-private-book-list';
    for (const item of data.items) {
      const entry = atom('li');
      const label = [item.number, item.label].filter(Boolean).join(' · ');
      entry.append(button(label, () => {
        state.problem = item.ordinal;
        refresh();
      }), atom('small', [item.chapter, item.has_korean ? (item.has_english === false ? 'KO' : 'KO · EN') : 'EN'].filter(Boolean).join(' · ')));
      rows.append(entry);
    }
    const counts = atom('p', data.total + ' ' + words.count);
    counts.className = 'al-muted';
    const pages = atom('nav');
    pages.className = 'al-private-controls';
    const jump = n => { state.page = n; refresh(); };
    const previous = button(words.previous, () => jump(state.page - 1));
    previous.disabled = state.page <= 1;
    const next = button(words.next, () => jump(state.page + 1));
    next.disabled = state.page >= data.pages;
    pages.append(previous, atom('span', data.page + ' / ' + data.pages), next);
    content.replaceChildren(bookPicker(), form, counts, data.items.length ? rows : atom('p', words.empty), pages);
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
        const volume = state.volume ? await get(API + '/books/' + book.id + '/volumes/' + state.volume, run) : null;
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
      if (state.book === 'feynman' && (error.status === 401 || error.status === 403)) showPublicLectures(run);
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
