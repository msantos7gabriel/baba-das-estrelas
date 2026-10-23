# baba-das-estrelas
Bot de gerenciamento do Baba das estrelas 

## Testes

Os testes simulam as mensagens do grupo sem enviar nada para o WhatsApp:

```bash
python manage.py test webhook_handler
```

Para rodar sem subir o Postgres, use SQLite:

```bash
DATABASE_URL=sqlite:///db.sqlite3 python manage.py test webhook_handler
```
