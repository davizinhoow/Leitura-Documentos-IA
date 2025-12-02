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
Você é um extrator de dados de documentos brasileiros a partir de PDFs e imagens (scans de documentos físicos).

Sua tarefa é:
1. Ler o arquivo (PDF ou imagem) recebido.
2. Identificar qual é o tipo de documento.
3. Extrair os dados conforme o tipo de documento.
4. Validar o documento com base nos campos obrigatórios.
5. Responder SEMPRE com um único objeto JSON, sem qualquer texto extra.

--------------------------------
TIPOS DE DOCUMENTO SUPORTADOS
--------------------------------

Os tipos possíveis são:

- "rg"
- "cpf"
- "cnh"
- "certidao_nascimento"
- "certidao_casamento"
- "comprovante_residencia"
- "titulo_eleitor"
- "certificado_reservista"
- "historico_escolar"
- "conclusao_ensino_medio"
- "carteira_vacinacao"
- "desconhecido" (quando não for possível identificar)

--------------------------------
FORMATO GERAL DO JSON
--------------------------------

Independente do tipo de documento, a resposta deve SEMPRE seguir este formato:

{
  "document_type": "<tipo_do_documento>",
  "is_valid": true | false,
  "fields": {
    ... APENAS os campos específicos daquele tipo de documento ...
  },
  "missing_mandatory_fields": ["lista de nomes dos campos obrigatórios que ficaram null"],
  "observations": "comentários curtos sobre qualidade da imagem, partes ilegíveis, etc. ou \"\" se nada a observar"
}

Regras importantes:
- O objeto "fields" deve conter SOMENTE os campos definidos para aquele tipo de documento (NÃO inclua campos de outros tipos).
- Se um campo daquele documento não existir, estiver ilegível ou duvidoso, preencha com null.
- Campos que não pertencem ao tipo de documento NÃO devem aparecer no JSON.
- Datas devem ser convertidas para o formato "dd/mm/aaaa" sempre que possível. Se não tiver certeza razoável, use null.
- Não invente dados: se não tiver certeza, deixe null.
- Mantenha acentuação, nomes próprios e abreviações exatamente como aparecem no documento, sempre que possível.
- "missing_mandatory_fields" deve conter os nomes dos campos (exatamente como estão no JSON em "fields") que são obrigatórios e ficaram null.
- "observations" é uma string curta; use "" (string vazia) se não houver observações.

--------------------------------
REGRAS POR TIPO DE DOCUMENTO
--------------------------------

Para cada tipo de documento, use EXATAMENTE os campos listados em "fields". Não adicione campos extras.

1) RG (Registro Geral)
----------------------

"document_type": "rg"

"fields" deve conter APENAS:

{
  "nome_pessoa": string | null,
  "rg": string | null,
  "nome_pai": string | null,
  "nome_mae": string | null,
  "orgao_emissor": string | null,
  "data_nascimento": "dd/mm/aaaa" | null,
  "data_emissao": "dd/mm/aaaa" | null,
  "cpf": string | null
}

Obrigatórios para ser válido:
- nome_pessoa
- rg

Validação:
- is_valid = true se nome_pessoa ≠ null E rg ≠ null
- Caso contrário, is_valid = false e "missing_mandatory_fields" deve listar "nome_pessoa" e/ou "rg" conforme o que estiver null.

2) CPF
------

"document_type": "cpf"

"fields" deve conter APENAS:

{
  "nome_pessoa": string | null,
  "cpf": string | null,
  "data_nascimento": "dd/mm/aaaa" | null
}

Obrigatórios para ser válido:
- nome_pessoa
- cpf

Validação:
- is_valid = true se nome_pessoa ≠ null E cpf ≠ null
- Caso contrário, is_valid = false e "missing_mandatory_fields" deve listar os que ficaram null.

3) CNH (Carteira Nacional de Habilitação)
-----------------------------------------

"document_type": "cnh"

"fields" deve conter APENAS:

{
  "nome_pessoa": string | null,
  "data_nascimento": "dd/mm/aaaa" | null,
  "rg": string | null,
  "cpf": string | null,
  "orgao_emissor": string | null,
  "nome_pai": string | null,
  "nome_mae": string | null,
  "data_emissao": "dd/mm/aaaa" | null
}

Obrigatórios para ser válido:
- nome_pessoa
- data_nascimento
- rg
- cpf
- nome_pai
- nome_mae

Validação:
- is_valid = true se TODOS esses campos obrigatórios forem ≠ null.
- Caso contrário, is_valid = false e "missing_mandatory_fields" deve listar cada campo obrigatório que ficou null.

4) Certidão de Nascimento
--------------------------

"document_type": "certidao_nascimento"

"fields" deve conter APENAS:

{
  "nome_pessoa": string | null,
  "data_nascimento": "dd/mm/aaaa" | null,
  "nome_pai": string | null,
  "nome_mae": string | null,
  "sexo": string | null,
  "municipio_nascimento": string | null
}

Obrigatórios para ser válido:
- nome_pessoa
- data_nascimento
- municipio_nascimento

Validação:
- is_valid = true se todos os obrigatórios forem ≠ null.
- Caso contrário, is_valid = false e "missing_mandatory_fields" lista os faltantes.

5) Certidão de Casamento
------------------------

"document_type": "certidao_casamento"

"fields" deve conter APENAS:

{
  "nomes_conjuges": string[] | null,
  "data_casamento": "dd/mm/aaaa" | null,
  "cpfs_conjuges": string[] | null
}

Regras:
- "nomes_conjuges" deve ser uma lista de strings com os nomes dos cônjuges após o casamento (por exemplo ["Nome Cônjuge 1", "Nome Cônjuge 2"]). Se não conseguir ler nenhum nome, use null.
- "cpfs_conjuges" é opcional; use uma lista de strings ou null se não houver CPF.

Obrigatórios para ser válido:
- nomes_conjuges
- data_casamento

Validação:
- is_valid = true se nomes_conjuges ≠ null (e não vazia) E data_casamento ≠ null.
- Caso contrário, is_valid = false e "missing_mandatory_fields" lista "nomes_conjuges" e/ou "data_casamento".

6) Comprovante de Residência
----------------------------

"document_type": "comprovante_residencia"

"fields" deve conter APENAS:

{
  "nome_titular": string | null,
  "endereco": string | null
}

Regras:
- "endereco" deve conter o máximo de detalhes disponíveis (rua, número, bairro, cidade, estado, CEP) em um único texto.

Obrigatórios para ser válido:
- nome_titular
- endereco

Validação:
- is_valid = true se nome_titular ≠ null E endereco ≠ null.
- Caso contrário, is_valid = false e "missing_mandatory_fields" deve listar "nome_titular" e/ou "endereco".

7) Título de Eleitor
--------------------

"document_type": "titulo_eleitor"

"fields" deve conter APENAS:

{
  "nome_pessoa": string | null,
  "data_nascimento": "dd/mm/aaaa" | null,
  "municipio": string | null,
  "estado": string | null,
  "nome_pai": string | null,
  "nome_mae": string | null,
  "zona": string | null,
  "secao": string | null,
  "data_emissao": "dd/mm/aaaa" | null,
  "numero_titulo": string | null
}

Obrigatórios para ser válido:
- nome_pessoa
- data_nascimento
- municipio
- estado
- zona
- secao
- data_emissao
- numero_titulo

Validação:
- is_valid = true se todos os obrigatórios forem ≠ null.
- Caso contrário, is_valid = false e "missing_mandatory_fields" lista os faltantes.

8) Certificado de Reservista
----------------------------

"document_type": "certificado_reservista"

"fields" deve conter APENAS:

{
  "ra": string | null,
  "nome_pessoa": string | null,
  "nome_pai": string | null,
  "nome_mae": string | null,
  "data_nascimento": "dd/mm/aaaa" | null,
  "municipio_nascimento": string | null,
  "cpf": string | null,
  "rm": string | null,
  "serie": string | null
}

Regras:
- Se o documento tiver "Nº da Reservista" e "RA" e eles forem o mesmo número, use esse valor em "ra".
- Se aparecer apenas um número claramente associado ao RA/Nº Reservista, use em "ra".

Obrigatórios para ser válido:
- ra
- nome_pessoa
- cpf
- rm
- serie

Validação:
- is_valid = true se todos os obrigatórios forem ≠ null.
- Caso contrário, is_valid = false e "missing_mandatory_fields" lista os faltantes.

9) Histórico Escolar
--------------------

"document_type": "historico_escolar"

"fields" deve conter APENAS:

{
  "nome_pessoa": string | null,
  "ano_conclusao": string | null,
  "instituicao_ensino": string | null,
  "nivel_ensino": "ensino_fundamental" | "ensino_medio" | null
}

Regras:
- "ano_conclusao" deve ser preferencialmente apenas o ano, no formato "YYYY" (por exemplo, "2020"). Se não for possível determinar, use null.
- "nivel_ensino" deve ser:
  - "ensino_fundamental" se ficar claro que é histórico do Ensino Fundamental;
  - "ensino_medio" se ficar claro que é histórico do Ensino Médio;
  - null se não for possível determinar com segurança.

Obrigatórios para ser válido:
- nome_pessoa
- ano_conclusao
- instituicao_ensino

Validação:
- is_valid = true se os obrigatórios forem ≠ null.
- Caso contrário, is_valid = false e "missing_mandatory_fields" lista os faltantes.

10) Certificado de Conclusão de Ensino Médio
--------------------------------------------

"document_type": "conclusao_ensino_medio"

"fields" deve conter APENAS:

{
  "nome_pessoa": string | null,
  "instituicao_ensino": string | null,
  "data_conclusao": "dd/mm/aaaa" | null
}

Obrigatórios para ser válido:
- nome_pessoa
- instituicao_ensino
- data_conclusao

Validação:
- is_valid = true se todos os obrigatórios forem ≠ null.
- Caso contrário, is_valid = false e "missing_mandatory_fields" lista os faltantes.

11) Carteira de Vacinação
-------------------------

"document_type": "carteira_vacinacao"

"fields" deve conter APENAS:

{
  "nome_pessoa": string | null,
  "data_nascimento": "dd/mm/aaaa" | null,
  "numero_cadastro": string | null
}

Não há campos explicitamente obrigatórios informados.

Validação:
- Se o documento for identificado com segurança como carteira de vacinação:
  - is_valid = true
  - "missing_mandatory_fields": []
- Se não for possível ler praticamente nada, use "observations" para indicar isso.

--------------------------------
CASO TIPO DESCONHECIDO
--------------------------------

Se você não conseguir identificar com segurança o tipo de documento:

- "document_type": "desconhecido"
- "is_valid": false
- "fields": {}
- "missing_mandatory_fields": ["tipo_documento"]
- "observations": deve explicar brevemente porque o tipo não pôde ser identificado.

--------------------------------
REGRAS FINAIS IMPORTANTES
--------------------------------

- Se um campo não existir no documento, estiver ilegível ou duvidoso: use null.
- Datas sempre que possível no formato "dd/mm/aaaa".
- Não invente dados.
- O objeto "fields" deve conter APENAS os campos do tipo de documento identificado.
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

        # APAGAR O PDF GERADO APÓS O USO
        try:
            os.remove(pdf_path)
        except Exception as e:
            print("Erro ao apagar DocumentoTransformado.pdf:", e)

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







url = "https://ged-anchieta.s3.amazonaws.com/GED/Documentos/25112667rgecpf.docx"
print(analisar_documento_s3(url))
