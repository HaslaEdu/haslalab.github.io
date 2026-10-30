/* Tighten the portal's supported sittings to complete, unambiguous paired rounds.
 * The caller supplies the actual portal grouping functions; no second exam selector lives here. */
const taskPattern = /^[A-Z][A-Za-z0-9]{0,3}$/;
const keyOf = tasks => [...tasks].sort().join('|');
const valid = tasks => tasks.length > 0 && tasks.length <= 4 &&
  tasks.every(task => typeof task === 'string' && taskPattern.test(task)) && new Set(tasks).size === tasks.length;
const partOf = (part, family) => new RegExp('^(' + family + ')(\\d*)([a-z]?)$').exec(part);
const stageOf = parsed => parsed[3] || 'default';

function buildPairCatalogue(data, {theoryGroups, examGroups, thyOf, examTask, officialTheoryParts}) {
  const catalogue = {};
  for (const [comp, competition] of Object.entries(data)) {
    // Separately named national/qualifying rounds need an explicit common round identifier.
    if (competition.rounds) continue;
    const years = {};
    for (const year of competition.years || []) {
      const files = thyOf(comp, year.y)?.f;
      if (!files) continue;
      // Source manifests exclude translated backup papers such as IPhO2025 T4.
      const published = officialTheoryParts?.(comp, year.y);
      const paperParts = Array.isArray(published) && published.length ? published : Object.keys(files);
      const theory = new Map(), lab = new Map();
      for (const tasks of theoryGroups(comp, year)) {
        if (!valid(tasks)) continue;
        const parsed = tasks.map(task => partOf(task, 'T|MC'));
        if (parsed.some(part => !part) || parsed.some(part => part[1] !== parsed[0][1] || stageOf(part) !== stageOf(parsed[0]))) continue;
        if (!tasks.every(task => typeof files[task]?.paper === 'string' && files[task].paper)) continue;
        const whole = tasks.length === 1 && !parsed[0][2];
        const siblings = paperParts.filter(task => {
          const part = partOf(task, 'T|MC');
          return part && part[2] && part[1] === parsed[0][1] && stageOf(part) === stageOf(parsed[0]) && !files[task]?.kx;
        });
        // A simulator-excluded problem, missing solution, or a >4-task split cannot become a full round.
        if (!whole && keyOf(tasks) !== keyOf(siblings)) continue;
        const stage = stageOf(parsed[0]);
        if (!theory.has(stage)) theory.set(stage, []);
        theory.get(stage).push({tasks, family: parsed[0][1]});
      }
      for (const group of examGroups(comp, year)) {
        if (group.some(problem => problem.thy || problem.theory)) continue;
        const tasks = group.map(examTask), parsed = group.map(problem => partOf(problem.id, 'E'));
        if (!valid(tasks) || parsed.some(part => !part) || parsed.some(part => stageOf(part) !== stageOf(parsed[0]))) continue;
        const stage = stageOf(parsed[0]);
        const siblings = (year.problems || []).filter(problem => {
          const part = partOf(problem.id, 'E');
          return part && stageOf(part) === stage;
        });
        // Observing/data-analysis/team simulators and unavailable experiments are not an entire E round.
        if (siblings.some(problem => problem.theory) || keyOf(tasks) !== keyOf(siblings.map(examTask))) continue;
        if (!lab.has(stage)) lab.set(stage, []);
        lab.get(stage).push(tasks);
      }
      const profiles = [];
      for (const [id, rounds] of theory) {
        const experiments = lab.get(id);
        if (!experiments?.length || new Set(rounds.map(round => round.family)).size !== 1) continue;
        const unique = sets => [...new Map(sets.map(tasks => [keyOf(tasks), [...tasks].sort()])).values()];
        profiles.push({id, theory:unique(rounds.map(round => round.tasks)), lab:unique(experiments)});
      }
      if (profiles.length) years[String(year.y)] = profiles.sort((a,b) => a.id.localeCompare(b.id));
    }
    if (Object.keys(years).length) catalogue[comp] = years;
  }
  return catalogue;
}

module.exports = {buildPairCatalogue};
