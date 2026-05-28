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
