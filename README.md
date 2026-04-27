# SteelCalculator

SteelCalculator — веб-приложение для расчета и оптимизации состава стали.  
Приложение запускается в Docker-контейнерах и использует PostgreSQL для хранения пользователей, вариантов расчета и результатов.

## Требования

На компьютере должны быть установлены:

- Docker Desktop
- Git
- браузер

Python и PostgreSQL отдельно устанавливать не нужно.

## Получение проекта

Клонировать репозиторий:

```powershell
cd D:\d
git clone https://github.com/dislikke/SteelCalculator2.git
cd SteelCalculator
````

Если проект передается архивом, нужно распаковать архив и перейти в папку проекта:

```powershell
cd D:\d\SteelCalculator
```

## Настройка окружения

В корне проекта должны находиться файлы `.env` и `.flaskenv`.

Пример файла `.env`:

```env
POSTGRES_DB=db
POSTGRES_USER=steel_user
POSTGRES_PASSWORD=steel_calc_2026
DATABASE_URL=postgresql://steel_user:steel_calc_2026@db:5432/db
SECRET_KEY=steel-calculator-secret-key
```

Пример файла `.flaskenv`:

```env
FLASK_APP=app
FLASK_ENV=development
FLASK_DEBUG=1
```

Если необходимо восстановить сохраненные данные, в корне проекта также должен находиться файл резервной копии:

```text
backup_before_stamp.sql
```

## Запуск через Docker Compose

Запустить приложение и базу данных:

```powershell
docker compose up -d --build
```

Применить миграции базы данных:

```powershell
docker compose exec web flask db upgrade
```

Если используется резервная копия базы данных, восстановить данные:

```powershell
docker exec -it steelcalculator-db-1 psql -U steel_user -d db -c "CREATE ROLE diana;"
Get-Content backup_before_stamp.sql | docker exec -i steelcalculator-db-1 psql -U steel_user -d db
```

После запуска приложение будет доступно по адресу:

```text
http://localhost:5002
```

## Запуск через Jenkins

Перед запуском через Jenkins нужно остановить обычный Docker Compose, если он был запущен:

```powershell
docker compose down
```

Запустить Jenkins:

```powershell
docker compose -f docker-compose.jenkins-host.yml up -d --build
```

Jenkins будет доступен по адресу:

```text
http://localhost:8080
```

Если Jenkins запрашивает первичный пароль, его можно получить командой:

```powershell
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

В Jenkins необходимо создать задачу типа `Pipeline`, указать файл `Jenkinsfile` и запустить сборку кнопкой `Build Now`.

После успешной сборки применить миграции:

```powershell
docker exec steel_web flask db upgrade
```

Если используется резервная копия базы данных, восстановить данные:

```powershell
docker exec -it steel_db psql -U steel_user -d db -c "CREATE ROLE diana;"
Get-Content backup_before_stamp.sql | docker exec -i steel_db psql -U steel_user -d db
```

После запуска через Jenkins приложение также будет доступно по адресу:

```text
http://localhost:5002
```

## Остановка приложения

Остановить обычный запуск:

```powershell
docker compose down
```

Остановить развертывание приложения, выполненное через Jenkins:

```powershell
docker compose -f deploy/docker-compose.jenkins.yml down
```

Остановить Jenkins:

```powershell
docker stop jenkins
```

## Сохранение данных

Данные PostgreSQL хранятся в Docker volume:

```text
steelcalculator_postgres-data
```

Обычный запуск через Docker Compose и запуск через Jenkins используют одно и то же хранилище базы данных. Поэтому данные сохраняются между перезапусками контейнеров.

Команда безопасной остановки:

```powershell
docker compose down
```

Команда, удаляющая данные базы:

```powershell
docker compose down -v
```

Команду `docker compose down -v` не следует использовать, если нужно сохранить пользователей, варианты расчета и результаты.

## Основные адреса

```text
Веб-приложение: http://localhost:5002
Jenkins:        http://localhost:8080
Prometheus:     http://localhost:9090
Grafana:        http://localhost:3000
```

```
```