# Sistema IoT - Monitoramento Industrial via MQTT

Projeto educacional de monitoramento de um tanque industrial usando MQTT,
SQLite e dashboard em Dash (Plotly), tudo orquestrado com Docker Compose.

## Arquitetura

```
Sensores Simulados (Python)
        ↓
   Publisher MQTT
        ↓
   Broker MQTT (Mosquitto)
        ↓
    Subscriber → SQLite
        ↓
  Dashboard (Dash/Plotly)
```

## Variáveis monitoradas

| Sensor      | Faixa            | Tópico MQTT                     |
|-------------|------------------|---------------------------------|
| Temperatura | 20 °C a 90 °C    | `industria/tanque/temperatura`  |
| Nível       | 0 % a 100 %      | `industria/tanque/nivel`        |
| Pressão     | 0 a 10 bar       | `industria/tanque/pressao`      |
| Vazão       | 0 a 200 L/min    | `industria/tanque/vazao`        |

## Como rodar

### Pré-requisitos
- Docker e Docker Compose instalados

### Subir o ambiente completo
```bash
docker compose up -d
```

### Parar tudo
```bash
docker compose down
```

---

## Passo 1 — Testando o Broker Mosquitto

Para verificar se o broker está funcionando:

### 1. Subir o broker
```bash
docker compose up -d mosquitto
```

### 2. Ver os logs
```bash
docker compose logs -f mosquitto
```
Você deve ver algo como `mosquitto version 2.x.x running`.

### 3. Testar publish/subscribe manualmente

Em um terminal, inscreva-se em todos os tópicos:
```bash
docker exec -it iot_mosquitto mosquitto_sub -h localhost -t "industria/tanque/+" -v
```

Em outro terminal, publique uma mensagem de teste:
```bash
docker exec -it iot_mosquitto mosquitto_pub -h localhost -t "industria/tanque/temperatura" -m "55.3"
```

Se a mensagem aparecer no primeiro terminal, o broker está funcionando.

### 4. Estrutura criada até aqui
```
projeto_iot/
├── docker-compose.yml
├── config.py
├── mosquitto/
│   ├── config/mosquitto.conf
│   ├── data/
│   └── log/
├── publisher/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── simulador.py
│   └── publisher.py
├── subscriber/     (vazio - Passo 3)
├── dashboard/      (vazio - Passo 4)
└── database/       (vazio - será criado pelo subscriber)
```

---

## Passo 2 — Publisher (sensores simulados)

### 1. Subir o publisher (vai subir junto com o mosquitto)
```bash
docker compose up -d --build
```

### 2. Ver os logs do publisher
```bash
docker compose logs -f publisher
```
Você deve ver linhas como:
```
→ industria/tanque/temperatura = 55.32 °C
→ industria/tanque/nivel = 60.47 %
→ industria/tanque/pressao = 4.99 bar
→ industria/tanque/vazao = 100.72 L/min
```
uma vez por segundo.

### 3. Verificar que as mensagens chegam ao broker
Em outro terminal:
```bash
docker exec -it iot_mosquitto mosquitto_sub -h localhost -t "industria/tanque/+" -v
```
Você verá os payloads JSON chegando em tempo real.

### Formato do payload
```json
{
  "valor": 67.3,
  "unidade": "°C",
  "timestamp": "2026-05-28T12:34:56.789Z",
  "topico": "industria/tanque/temperatura",
  "sensor": "temperatura"
}
```

---

## Passo 3 — Subscriber + SQLite

### 1. Subir o subscriber
```bash
docker compose up -d --build
```
Vai (re)construir e subir os 3 serviços: mosquitto, publisher e subscriber.

### 2. Ver logs do subscriber
```bash
docker compose logs -f subscriber
```
Saída esperada:
```
Banco inicializado em /data/tanque.db
Conectado ao broker mosquitto:1883
Inscrito no tópico 'industria/tanque/+'
← industria/tanque/temperatura = 55.32 °C (salvo, id auto)
← industria/tanque/nivel = 60.47 % (salvo, id auto)
...
```

### 3. Inspecionar o banco

O arquivo do SQLite fica em `./database/tanque.db` no host.

Contar leituras:
```bash
sqlite3 database/tanque.db "SELECT COUNT(*) FROM leituras;"
```

Ver as últimas 5 leituras:
```bash
sqlite3 database/tanque.db "SELECT sensor, valor, unidade, timestamp FROM leituras ORDER BY id DESC LIMIT 5;"
```

Ver a tabela toda formatada:
```bash
sqlite3 -header -column database/tanque.db "SELECT * FROM leituras ORDER BY id DESC LIMIT 10;"
```

### Schema da tabela `leituras`

| Coluna       | Tipo    | Descrição                                          |
|--------------|---------|----------------------------------------------------|
| id           | INTEGER | Chave primária autoincremento                      |
| timestamp    | TEXT    | ISO 8601 do payload (quando o sensor mediu)        |
| recebido_em  | TEXT    | ISO 8601 de quando o subscriber recebeu (auditoria)|
| sensor       | TEXT    | temperatura, nivel, pressao ou vazao               |
| valor        | REAL    | Valor numérico da leitura                          |
| unidade      | TEXT    | Unidade da medida (°C, %, bar, L/min)              |
| topico       | TEXT    | Tópico MQTT completo                               |

---

## Passo 4 — Dashboard Dash

### 1. Subir o stack completo
```bash
docker compose up -d --build
```
Vai construir e iniciar os 4 serviços: `mosquitto`, `publisher`, `subscriber` e `dashboard`.

### 2. Abrir o dashboard
Acessar no navegador: **http://localhost:8050**

### 3. O que você verá

**Header:**
- Título do sistema
- Pill verde/vermelha: status do broker (conectado/desconectado)
- Texto: tempo desde o último pacote recebido

**Painel de alarmes:**
- Texto verde "Sem alarmes ativos" quando tudo ok
- Pills amarelas para avisos (nível < 20%)
- Pills vermelhas piscando para alarmes (temp > 80°C, pressão > 8 bar)

**4 indicadores em tempo real:**
| Sensor      | Visualização                      |
|-------------|-----------------------------------|
| Temperatura | Gauge circular (20–90 °C)         |
| Nível       | Barra vertical (0–100%)           |
| Pressão     | Numérico + bullet gauge (0–10 bar)|
| Vazão       | Medidor analógico (0–200 L/min)   |

Cada card mostra também tópico MQTT + timestamp.

**2 gráficos históricos (últimos 60 pontos):**
- Temperatura + Pressão (eixos Y duplos)
- Nível + Vazão (eixos Y duplos)

### 4. Verificar status MQTT funcionando

Pare o publisher e veja o status mudar para "Broker desconectado":
```bash
docker compose stop publisher
# Aguarde uns 5 segundos e olhe o dashboard
docker compose start publisher
```

### 5. Customizar limites de alarme
Edite `dashboard/alarmes.py`:
```python
TEMP_CRITICA = 80.0
NIVEL_BAIXO = 20.0
PRESSAO_CRITICA = 8.0
```
Depois reconstrua só o dashboard:
```bash
docker compose up -d --build dashboard
```
