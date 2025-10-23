@echo off
echo Создание бэкапа прода...
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres -d staffprobot_prod > /tmp/staffprobot_prod_backup_$(date +%Y%m%d_%H%M%S).sql'

echo Копирование бэкапа...
c:\tools\putty\pscp staffprobot@staffprobot.ru:/tmp/staffprobot_prod_backup_*.sql .

echo Очистка dev БД...
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo Восстановление из бэкапа...
for %%f in (staffprobot_prod_backup_*.sql) do (
    echo Восстанавливаю %%f
    docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d staffprobot_dev < %%f
    goto :done
)
:done

echo Готово!
