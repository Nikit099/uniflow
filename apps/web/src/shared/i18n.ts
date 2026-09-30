import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

export const resources = {
  ru: { translation: {
    student: 'Студент', staff: 'Сотрудник', admin: 'Администратор', login: 'Войти', username: 'Логин', password: 'Пароль', loginFailed: 'Неверный логин или пароль', demoAccounts: 'Демо-аккаунты', notifications: 'Уведомления',
    nextAction: 'Следующее действие', myCases: 'Мои дела', open: 'Открыть дело', noCases: 'Нет активных дел', allCases: 'Все дела', queueSearch: 'Поиск по студенту или делу', emptyQueue: 'Очередь пуста', noMatchingCases: 'По выбранным условиям дела не найдены', emptyProcedures: 'Версии процедур ещё не добавлены', emptySources: 'Источники ещё не добавлены', emptyNotifications: 'Уведомлений пока нет',
    progress: 'Готовность', deadline: 'Срок', requirements: 'Чек-лист', upload: 'Добавить документ', uploadFailed: 'Не удалось загрузить файл. Проверьте его тип и размер и попробуйте ещё раз.', submit: 'Отправить комплект', submitted: 'Отправлено', casesStarted: 'Создано дел',
    source: 'Источник', verifiedNotice: 'Университет проверил комплект. Это не решение госоргана.', maxLoginFailed: 'Не удалось войти через MAX.', serviceUnavailable: 'Сервис временно недоступен. Повторите попытку позже.',
    queue: 'Очередь проверки', waiting: 'Ждут проверки', changes: 'На исправлении', verified: 'Проверены', assign: 'Взять в работу',
    accept: 'Принять', requestChanges: 'Вернуть на исправление', reason: 'Что именно нужно исправить', sendReason: 'Отправить', cancel: 'Отмена', verify: 'Подтвердить проверку комплекта',
    procedures: 'Версии процедур', sources: 'Библиотека источников', analytics: 'Аналитика', importJson: 'Импорт JSON', exportJson: 'Экспорт JSON', activate: 'Активировать', logout: 'Выйти', retry: 'Повторить',
    ai: 'AI-помощник', explain: 'Объяснить проще', aiUnavailable: 'AI-помощник сейчас недоступен',
    uploadWarning: 'Только демофайлы. Не загружайте реальные документы.',
    unsupported: 'Этот сценарий пока требует проверки сотрудником.', language: 'English', history: 'История', loading: 'Загрузка…', error: 'Не удалось загрузить данные.',
  } },
  en: { translation: {
    student: 'Student', staff: 'Staff', admin: 'Administrator', login: 'Log in', username: 'Username', password: 'Password', loginFailed: 'Incorrect username or password', demoAccounts: 'Demo accounts', notifications: 'Notifications',
    nextAction: 'Next action', myCases: 'My cases', open: 'Open case', noCases: 'No active cases', allCases: 'All cases', queueSearch: 'Search student or case', emptyQueue: 'The review queue is empty', noMatchingCases: 'No cases match these filters', emptyProcedures: 'No procedure versions have been added', emptySources: 'No sources have been added', emptyNotifications: 'No notifications yet',
    progress: 'Progress', deadline: 'Deadline', requirements: 'Checklist', upload: 'Add document', uploadFailed: 'Could not upload this file. Check its type and size, then try again.', submit: 'Submit package', submitted: 'Submitted', casesStarted: 'Cases started',
    source: 'Source', verifiedNotice: 'The university reviewed this package. This is not a government decision.', maxLoginFailed: 'Could not sign in with MAX.', serviceUnavailable: 'The service is temporarily unavailable. Try again later.',
    queue: 'Review queue', waiting: 'Waiting for review', changes: 'Needs changes', verified: 'Verified', assign: 'Assign to me',
    accept: 'Accept', requestChanges: 'Request changes', reason: 'What needs to be corrected', sendReason: 'Submit', cancel: 'Cancel', verify: 'Confirm university review',
    procedures: 'Procedure versions', sources: 'Source library', analytics: 'Analytics', importJson: 'Import JSON', exportJson: 'Export JSON', activate: 'Activate', logout: 'Log out', retry: 'Retry',
    ai: 'AI assistant', explain: 'Explain simply', aiUnavailable: 'AI assistant is currently unavailable',
    uploadWarning: 'Demo files only. Do not upload real documents.',
    unsupported: 'This scenario currently requires staff review.', language: 'Русский', history: 'History', loading: 'Loading…', error: 'Could not load data.',
  } },
}

const savedLanguage = typeof localStorage?.getItem === 'function' ? localStorage.getItem('language') : null
void i18n.use(initReactI18next).init({ resources, lng: savedLanguage || 'ru', fallbackLng: 'ru', interpolation: { escapeValue: false } })
export default i18n
