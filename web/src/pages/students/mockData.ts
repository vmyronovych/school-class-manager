// Статичні дані мокапу (docs/mockups.md) у форматі з docs/plan.md: логін прізвище.ім'я.рік
// (> 20 символів — ім'я до ініціала), клас <рік>-<клас>. У сесії 3 M1 замінюються на GET /api/students.

export type StudentStatus = 'Active' | 'Locked' | 'Disabled' | 'NeverLoggedIn';

export interface StudentRow {
  login: string;
  name: string;
  classCode: string;
  classDisplay: string;
  status: StudentStatus;
  lastLogon: string;
  lastLogonPc?: string;
  folderSize: string;
  folderFiles?: number;
  passwordChangedAt?: string;
}

export const mockSummary = { accounts: 46, classes: 2, disabled: 3 };

export const mockClasses = [
  { code: '2025-3a', display: '3-А' },
  { code: '2025-4a', display: '4-А' },
];

export const mockStudents: StudentRow[] = [
  { login: 'ivanenko.petro.2016', name: 'Іваненко Петро', classCode: '2025-4a', classDisplay: '4-А', status: 'Active', lastLogon: 'Сьогодні 09:14', lastLogonPc: 'KAB-07', folderSize: '12 MB', folderFiles: 38, passwordChangedAt: '08.09.2026' },
  { login: 'kovalenko.m.2016', name: 'Коваленко Марія', classCode: '2025-4a', classDisplay: '4-А', status: 'Active', lastLogon: 'Сьогодні 09:12', folderSize: '9 MB' },
  { login: 'bondar.oleksii.2016', name: 'Бондар Олексій', classCode: '2025-4a', classDisplay: '4-А', status: 'Locked', lastLogon: 'Сьогодні 09:10', folderSize: '4 MB' },
  { login: 'melnyk.sofiia.2016', name: 'Мельник Софія', classCode: '2025-4a', classDisplay: '4-А', status: 'Active', lastLogon: 'Пн 15.09, 10:02', folderSize: '21 MB' },
  { login: 'tkachenko.d.2016', name: 'Ткаченко Дмитро', classCode: '2025-4a', classDisplay: '4-А', status: 'Active', lastLogon: 'Пн 15.09, 10:01', folderSize: '7 MB' },
  { login: 'shevchenko.oleh.2017', name: 'Шевченко Олег', classCode: '2025-3a', classDisplay: '3-А', status: 'Active', lastLogon: 'Пн 15.09, 11:30', folderSize: '3 MB' },
  { login: 'kravets.anna.2017', name: 'Кравець Анна', classCode: '2025-3a', classDisplay: '3-А', status: 'Active', lastLogon: 'Пн 15.09, 11:29', folderSize: '5 MB' },
  { login: 'lysenko.ivan.2017', name: 'Лисенко Іван', classCode: '2025-3a', classDisplay: '3-А', status: 'NeverLoggedIn', lastLogon: '—', folderSize: '0 MB' },
  { login: 'polishchuk.d.2017', name: 'Поліщук Дарина', classCode: '2025-3a', classDisplay: '3-А', status: 'Active', lastLogon: 'Пн 15.09, 11:28', folderSize: '6 MB' },
  { login: 'hnatiuk.maksym.2017', name: 'Гнатюк Максим', classCode: '2025-3a', classDisplay: '3-А', status: 'Disabled', lastLogon: 'Чт 04.09, 11:40', folderSize: '2 MB' },
];

export const mockSnapshots = ['Сьогодні 09:00', 'Вчора 17:00', 'Пн 15.09, 12:00'];
