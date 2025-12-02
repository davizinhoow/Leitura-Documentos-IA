import os
import uuid
import requests
import httpx
import mimetypes
import win32com.client
import google.genai as genai
from google.genai import types



client = genai.Client(api_key="AIzaSyARFkkSRjtqCkkoeUKki1mYhNJ9CwlUlLo")

prompt = """
Você é um extrator de dados de documentos de identificação brasileiros.

SEMPRE receba como entrada um documento digital ou escaneado (imagem ou PDF) e:

1. Identifique o tipo de documento:
   - "RG"
   - "CPF"
   - "CNH"
   - ou "desconhecido" caso não seja possível identificar

2. A partir do tipo identificado, extraia SOMENTE os campos especificados abaixo.

3. Preencha os campos com base no conteúdo visual do documento (OCR), mesmo que os textos estejam com variações de formatação, maiúsculas/minúsculas ou abreviações.

4. Utilize o seguinte formato de resposta, SEM QUALQUER TEXTO EXTRA, APENAS JSON:

{
  "document_type": "RG | CPF | CNH | desconhecido",
  "is_valid": true | false,
  "fields": {
    "nome_pessoa": null ou "texto",
    "registro_geral": null ou "texto",
    "nome_pai": null ou "texto",
    "nome_mae": null ou "texto",
    "orgao_emissor": null ou "texto",
    "data_nascimento": null ou "dd/mm/aaaa",
    "data_emissao": null ou "dd/mm/aaaa",
    "cpf": null ou "texto"
  },
  "missing_mandatory_fields": ["lista de campos obrigatórios não encontrados"],
  "observations": "mensagens breves sobre qualidade da imagem, dúvidas ou inconsistências identificadas"
}

- Se um campo não existir no documento, escreva null nesse campo.
- Datas devem ser convertidas para o formato "dd/mm/aaaa" sempre que possível. Se não for possível ter certeza razoável, deixe o campo como null.
- Não invente dados: se não tiver certeza, deixe null.

-------------------------------
REGRAS POR TIPO DE DOCUMENTO
-------------------------------

1) RG (Registro Geral)

Campos a extrair:
- nome_pessoa                (obrigatório)
- registro_geral             (obrigatório)
- nome_pai                   (opcional)
- nome_mae                   (opcional)
- orgao_emissor              (opcional)
- data_nascimento            (opcional)
- data_emissao               (opcional, menos importante)
- cpf                        (opcional – só preencha se aparecer no RG)

Validação do RG:
- is_valid = true SE E SOMENTE SE:
  - nome_pessoa NÃO for null
  - E registro_geral NÃO for null
- Caso contrário:
  - is_valid = false
  - missing_mandatory_fields deve listar quais obrigatórios estão faltando (por exemplo: ["nome_pessoa", "registro_geral"]).

2) CPF

Campos a extrair:
- nome_pessoa                (opcional)
- cpf                        (obrigatório)
- data_nascimento            (opcional)

Validação do CPF:
- is_valid = true SE E SOMENTE SE:
  - cpf NÃO for null
- Caso contrário:
  - is_valid = false
  - missing_mandatory_fields = ["cpf"] se o número de CPF não for encontrado.

3) CNH (Carteira Nacional de Habilitação)

Campos a extrair:
- nome_pessoa                (obrigatório)
- data_nascimento            (opcional)
- registro_geral             (obrigatório se aparecer explícito como RG)
- cpf                        (obrigatório se aparecer explícito na CNH)
- orgao_emissor              (opcional – exemplo: SSP, DETRAN, etc.)
- nome_pai                   (opcional)
- nome_mae                   (opcional)
- data_emissao               (opcional, se existir uma data claramente associada à emissão)

Observação importante sobre CNH:
- Se a CNH não contiver explicitamente o RG ou o CPF, deixe esses campos como null.
- Para validação, considere:
  - is_valid = true se:
    - nome_pessoa NÃO for null
    - E pelo menos um entre registro_geral ou cpf NÃO for null
  - Caso contrário:
    - is_valid = false
    - missing_mandatory_fields deve listar "nome_pessoa" e também "registro_geral" e/ou "cpf" se estiverem ausentes conforme a regra acima.

-------------------------------
REGRAS GERAIS
-------------------------------

- Se não for possível identificar com segurança se o documento é RG, CPF ou CNH:
  - document_type = "desconhecido"
  - is_valid = false
  - missing_mandatory_fields pode ser ["tipo_documento"] ou uma mensagem indicando que o tipo não pôde ser determinado.
- Não inclua nenhum texto explicativo fora do JSON.
- Não escreva comentários, títulos ou descrições antes ou depois do JSON.
- Não traduza nem adapte os dados do documento, apenas normalize datas.
- Mantenha acentuação, nomes próprios e abreviações exatamente como aparecem no documento, sempre que possível.

Agora, sempre que receber um PDF ou imagem de documento, siga essas regras e devolva apenas o JSON nesse formato.

"""




def docx_to_pdf_from_url_word(url, pdf_name='DocumentoTransformado.pdf'):
    project_dir = os.getcwd()

    file_id = str(uuid.uuid4())
    docx_path = os.path.join(project_dir, f"{file_id}.docx")
    pdf_path = os.path.join(project_dir, pdf_name)

    r = requests.get(url)
    with open(docx_path, "wb") as f:
        f.write(r.content)

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False

    try:
        doc = word.Documents.Open(docx_path)
        doc.SaveAs(pdf_path, FileFormat=17)
        doc.Close()
    finally:
        word.Quit()

    try:
        os.remove(docx_path)
    except Exception as e:
        print("Erro ao apagar DOCX temporário:", e)

    return pdf_path



def analisar_documento_s3(url):
    ext = url.lower().split(".")[-1]



    if ext == "pdf":
        doc_data = httpx.get(url).content

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=doc_data,
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )
        return response


    elif ext == "docx":
        pdf_path = docx_to_pdf_from_url_word(
            url,
            pdf_name="DocumentoTransformado.pdf"
        )

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )

        return response

   

    elif ext in ["jpg", "jpeg", "png", "tiff"]:
        image_bytes = requests.get(url).content

        
        mime_type = mimetypes.guess_type(url)[0] or "image/jpeg"

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                ),
                prompt
            ]
        )

        return response

 


    else:
        return {
            "error": True,
            "message": f"Tipo de arquivo '{ext}' não suportado. Permitido: PDF, DOCX, JPG, JPEG, PNG, TIFF."
        }





url = "https://ged-anchieta.s3.amazonaws.com/GED/Documentos/26032443CPF.jpg"
print(analisar_documento_s3(url))
