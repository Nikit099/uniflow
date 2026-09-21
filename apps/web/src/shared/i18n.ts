import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

export const resources = {
  ru: { translation: {
    demo: 'Демонстрационная конфигурация · синтетические данные · не является системой университета или МВД',
    title: 'Понятный путь по документам', subtitle: 'UniFlow показывает следующее действие и сохраняет контекст проверки.',
    student: 'Студент', staff: 'Сотрудник', admin: 'Администратор', login: 'Войти в демо',
    nextAction: 'Следующее действие', myCases: 'Мои дела', open: 'Открыть дело', noCases: 'Нет активных дел',
    progress: 'Готовность', deadline: 'Срок', requirements: 'Чек-лист', upload: 'Добавить документ', submit: 'Отправить комплект',
    source: 'Источник', verifiedNotice: 'Университет подтвердил готовность комплекта. Это не является подтверждением решения государственного органа.',
    queue: 'Очередь проверки', waiting: 'Ждут проверки', changes: 'На исправлении', verified: 'Проверены', assign: 'Взять в работу',
    accept: 'Принять', requestChanges: 'Вернуть на исправление', reason: 'Что именно нужно исправить', verify: 'Подтвердить проверку комплекта',
    procedures: 'Версии процедур', sources: 'Библиотека источников', analytics: 'Аналитика', logout: 'Выйти', retry: 'Повторить',
    ai: 'AI-помощник', explain: 'Объяснить проще', aiUnavailable: 'AI-помощник сейчас недоступен',
    uploadWarning: 'Не загружайте реальные паспортные или миграционные документы. Используйте только демонстрационные файлы.',
    unsupported: 'Этот сценарий пока требует проверки сотрудником.', language: 'English', history: 'История', loading: 'Загрузка…', error: 'Не удалось загрузить данные.',
  } },
  en: { translation: {
    demo: 'Demo configuration · synthetic data · not an official university or government system',
    title: 'A clear path through paperwork', subtitle: 'UniFlow shows the next action and preserves review context.',
    student: 'Student', staff: 'Staff', admin: 'Administrator', login: 'Enter demo',
    nextAction: 'Next action', myCases: 'My cases', open: 'Open case', noCases: 'No active cases',
    progress: 'Progress', deadline: 'Deadline', requirements: 'Checklist', upload: 'Add document', submit: 'Submit package',
    source: 'Source', verifiedNotice: 'The university confirmed the package is ready. This is not confirmation of a government authority decision.',
    queue: 'Review queue', waiting: 'Waiting for review', changes: 'Needs changes', verified: 'Verified', assign: 'Assign to me',
    accept: 'Accept', requestChanges: 'Request changes', reason: 'What needs to be corrected', verify: 'Confirm university review',
    procedures: 'Procedure versions', sources: 'Source library', analytics: 'Analytics', logout: 'Log out', retry: 'Retry',
    ai: 'AI assistant', explain: 'Explain simply', aiUnavailable: 'AI assistant is currently unavailable',
    uploadWarning: 'Do not upload real passport or migration documents. Use demo files only.',
    unsupported: 'This scenario currently requires staff review.', language: 'Русский', history: 'History', loading: 'Loading…', error: 'Could not load data.',
  } },
}

const savedLanguage = typeof localStorage?.getItem === 'function' ? localStorage.getItem('language') : null
void i18n.use(initReactI18next).init({ resources, lng: savedLanguage || 'ru', fallbackLng: 'ru', interpolation: { escapeValue: false } })
export default i18n
