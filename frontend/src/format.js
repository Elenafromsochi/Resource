// Небольшие форматтеры дат/времени для интерфейса.
const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
const DOW = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб']

export function parse(iso) { return new Date(iso + 'T00:00:00') }

export function dayNum(iso) { return parse(iso).getDate() }
export function monShort(iso) { return MONTHS_SHORT[parse(iso).getMonth()] }
export function dowShort(iso) { return DOW[parse(iso).getDay()] }

export function human(iso) {
  const d = parse(iso)
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`
}

export function relativeDay(iso) {
  const d = parse(iso)
  const t = new Date(); t.setHours(0, 0, 0, 0)
  const diff = Math.round((d - t) / 86400000)
  if (diff === 0) return 'Сегодня'
  if (diff === 1) return 'Завтра'
  if (diff === -1) return 'Вчера'
  if (diff > 1 && diff <= 6) return `Через ${diff} дн.`
  return human(iso)
}

export function msgTime(ts) {
  const d = new Date(ts)
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

export { MONTHS, DOW }
