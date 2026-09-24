// Статичні дані мокапу (docs/mockups.md). У сесії 3 M1 замінюються на GET /api/students.

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
  { code: '3a', display: '3-А' },
  { code: '4a', display: '4-А' },
];

export const mockStudents: StudentRow[] = [
  { login: '4a.ivanenko', name: 'Іваненко Петро', classCode: '4a', classDisplay: '4-А', status: 'Active', lastLogon: 'Сьогодні 09:14', lastLogonPc: 'KAB-07', folderSize: '12 MB', folderFiles: 38, passwordChangedAt: '08.09.2026' },
  { login: '4a.kovalenko', name: 'Коваленко Марія', classCode: '4a', classDisplay: '4-А', status: 'Active', lastLogon: 'Сьогодні 09:12', folderSize: '9 MB' },
  { login: '4a.bondar', name: 'Бондар Олексій', classCode: '4a', classDisplay: '4-А', status: 'Locked', lastLogon: 'Сьогодні 09:10', folderSize: '4 MB' },
  { login: '4a.melnyk', name: 'Мельник Софія', classCode: '4a', classDisplay: '4-А', status: 'Active', lastLogon: 'Пн 15.09, 10:02', folderSize: '21 MB' },
  { login: '4a.tkachenko', name: 'Ткаченко Дмитро', classCode: '4a', classDisplay: '4-А', status: 'Active', lastLogon: 'Пн 15.09, 10:01', folderSize: '7 MB' },
  { login: '3a.shevchenko', name: 'Шевченко Олег', classCode: '3a', classDisplay: '3-А', status: 'Active', lastLogon: 'Пн 15.09, 11:30', folderSize: '3 MB' },
  { login: '3a.kravets', name: 'Кравець Анна', classCode: '3a', classDisplay: '3-А', status: 'Active', lastLogon: 'Пн 15.09, 11:29', folderSize: '5 MB' },
  { login: '3a.lysenko', name: 'Лисенко Іван', classCode: '3a', classDisplay: '3-А', status: 'NeverLoggedIn', lastLogon: '—', folderSize: '0 MB' },
  { login: '3a.polishchuk', name: 'Поліщук Дарина', classCode: '3a', classDisplay: '3-А', status: 'Active', lastLogon: 'Пн 15.09, 11:28', folderSize: '6 MB' },
  { login: '3a.hnatiuk', name: 'Гнатюк Максим', classCode: '3a', classDisplay: '3-А', status: 'Disabled', lastLogon: 'Чт 04.09, 11:40', folderSize: '2 MB' },
];

export const mockSnapshots = ['Сьогодні 09:00', 'Вчора 17:00', 'Пн 15.09, 12:00'];
