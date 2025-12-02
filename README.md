# 🧾 Validador Automático de Documentos – IA com Gemini 2.5  
**Desenvolvido por: Davi Ferreira Freitas e Mateus Thomasini Modesto**

---

## 📌 Sobre o Projeto

Este projeto tem como objetivo substituir a ferramenta atual usada pelo setor de T.I. (Desenvolvimento) para **validação automática de documentos enviados pelos alunos** no sistema web da instituição.

A solução utiliza **IA (Google Gemini 2.5)** para identificar o tipo do documento, extrair campos específicos e validar automaticamente se os dados obrigatórios estão presentes.

O sistema lê **PDF, DOCX e imagens (JPG, PNG, TIFF)**, normaliza as informações e retorna somente um **JSON padronizado**, facilitando integração com outros sistemas.

---

## 🧠 Como funciona

1. O usuário envia um documento (PDF, imagem ou DOCX).  
2. O sistema converte DOCX automaticamente para PDF quando necessário.  
3. O arquivo é enviado ao modelo **Gemini 2.5 Flash**.  
4. A IA identifica o tipo do documento (RG, CPF, CNH ou desconhecido).  
5. Apenas os campos relevantes são extraídos conforme regras do documento.  
6. O sistema valida e retorna um JSON estruturado contendo:
   - Tipo do documento  
   - Dados extraídos  
   - Campos obrigatórios ausentes  
   - Status de validade  
   - Observações sobre inconsistências ou qualidade da imagem  

---

## 📄 Tipos de Documentos Suportados

### ✔️ **RG**
Campos extraídos: nome, RG, nome dos pais, órgão emissor, data de nascimento, data de emissão e CPF (quando existir).

### ✔️ **CPF**
Campos extraídos: nome, CPF e data de nascimento.

### ✔️ **CNH**
Campos extraídos: nome, RG, CPF, nome dos pais, órgão emissor, nascimento, emissão.

---

## ➕ Documentos planejados (conforme PDF oficial)

- Certidão de Nascimento  
- Certidão de Casamento  
- Comprovante de Residência  
- Título de Eleitor  
- Certificado Reservista  
- Histórico Escolar  
- Declaração/Conclusão Ensino Médio  
- Carteira de Vacinação  

> *Atualmente o código implementa RG, CPF e CNH — mas a arquitetura está pronta para expansão.*

---

## 🛠 Tecnologias Utilizadas

- Python 3  
- Google Gemini 2.5 Flash  
- Requests / HTTPX  
- Win32com (conversão automática DOCX → PDF via Word)  
- UUID / OS / mimetypes  

---

## 🧩 Arquitetura Simplificada

Documento (PDF / Imagem / DOCX)
↓
Processamento
↓
Conversão para PDF (se DOCX)
↓
Envio ao Gemini
↓
Detecção do tipo + OCR + Extração
↓
Validação dos campos obrigatórios
↓
Retorno em JSON padronizado

---

## 🚀 Como Executar o Projeto

### 1. Instale as dependências
```bash
pip install google-genai httpx requests pywin32
```
### 2. Configure sua API key do Gemini
No arquivo Python:
```python
client = genai.Client(api_key="SUA_CHAVE_AQUI")
```
### 3. Execute o arquivo principal
```bash
python leitura_validacao_documentos.py
```

---

## 🔧 Exemplo de Uso

```python
url = "https://meu-servidor.com/documento.pdf"
print(analisar_documento_s3(url))
```
### Exemplo de saída (JSON)
```json
{
  "document_type": "RG",
  "is_valid": true,
  "fields": {
    "nome_pessoa": "FULANO DE TAL",
    "registro_geral": "12.345.678-9",
    "nome_pai": "JOÃO TAL",
    "nome_mae": "MARIA TAL",
    "orgao_emissor": "SSP",
    "data_nascimento": "10/02/1999",
    "data_emissao": "15/03/2016",
    "cpf": null
  },
  "missing_mandatory_fields": [],
  "observations": ""
}
```

---

## 📌 Estrutura do Projeto

```
📁 projeto-validacao-documentos
 ├── 📄 leitura_validacao_documentos.py
 ├── 📄 Detalhamento Técnico.pdf
 ├── README.md   ← (este arquivo)
```

---

## 📜 Licença

Este projeto é de uso interno/institucional.
Licenciamento pode ser ajustado conforme necessidade.
