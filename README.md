# Plano de Corte DXF API

## Como usar

1. Suba este projeto no Railway.
2. No Railway, vá em **Variables** e crie a variável `service_account.json` com o conteúdo da sua chave.
3. A API terá um endpoint POST `/compor` que recebe:

```
{
  "arquivos": [
    { "nome": "etiqueta1.dxf", "posicao": 1 },
    { "nome": "etiqueta2.dxf", "posicao": 2 }
  ]
}
```

4. A resposta será o link para o arquivo DXF final gerado no Google Drive.