# Loja da Maria

Um aplicativo simples para a Maria registrar e consultar as vendas da loja de acessórios, no lugar da planilha do Excel.

## O problema

A Maria anota cada venda em uma linha da planilha, do jeito que lembra. Com o tempo, a planilha ficou difícil de usar:

- a mesma informação aparece escrita de vários jeitos (`loja`, `presencial`, `ela veio buscar`);
- as datas têm oito formatos diferentes, incluindo `ontem`, `hj` e `segunda`;
- há informação na coluna errada, como código de rastreio no lugar do nome;
- achar um pagamento ou um rastreio no meio das linhas dá trabalho.

Ela não entende de tecnologia, então a solução precisa ser usada sem ajuda.

## A solução

O aplicativo tem duas telas.

**Registrar venda.** Um formulário em que ela escolhe em vez de digitar:

- o produto vem de uma lista com o que ela já vendeu, e o preço de sempre aparece sozinho (ela pode mudar);
- data, forma de pagamento e entrega são botões;
- os campos de cartão, parcelas e rastreio só aparecem quando fazem sentido;
- produto, valor e nome são obrigatórios.

**Minhas vendas.** A tabela com todas as vendas, a mais recente em cima:

- uma caixa de pesquisa única, que procura por nome, produto, rastreio, data, pagamento ou observação, sem se importar com acentos;
- quatro botões de filtro: Todas, Para conferir, Quem me deve e Envios sem rastreio;
- ao marcar uma linha, os campos daquela venda aparecem para corrigir, completar (por exemplo, o rastreio que chegou depois) ou apagar;
- um botão para baixar todas as vendas em uma planilha do Excel, já limpa.

## O que foi feito com a planilha antiga

As vendas que a Maria já tinha foram levadas para o aplicativo. O arquivo original não é alterado. Das 72 linhas, uma estava vazia; as outras 71 viraram 69 vendas, 1 devolução e 1 compra de fornecedor.

A limpeza segue três níveis:

1. **Corrige sozinha o que é certo.** `R$ 35` e `35,00` viram o mesmo valor; `loja`, `presencial` e `ela veio buscar` viram "Retirada na loja"; `brinc argola` vira "Brinco argola"; `credito 3x visa` é separado em forma, cartão e parcelas.
2. **Deduz e marca para conferir.** `ontem` e `hj` recebem a data da linha anterior; `35+12 frete` é somado; uma linha igual a outra é mantida, mas avisada.
3. **Não adivinha.** Venda sem data, sem valor ou com `segunda` no lugar da data fica em branco e marcada.

As vendas marcadas (16 logo após a migração) aparecem no filtro **Para conferir**, com o motivo da dúvida e a linha como estava na planilha. A Maria corrige ou confirma com "Está certo assim".

Apelidos como "a vizinha" e "tia da Ana" foram mantidos, porque é assim que ela conhece as clientes.

## Como rodar

É preciso ter o Python instalado (testado na versão 3.14).

1. Abra um terminal na pasta do projeto e instale as bibliotecas:

   ```
   pip install -r requirements.txt
   ```

2. Importe a planilha da Maria. Só é necessário na primeira vez, quando o arquivo `dados/vendas.db` ainda não existe:

   ```
   python migrar.py
   ```

   O comando procura o arquivo `Vendas_da_maria*.xlsx` na pasta do projeto ou em uma subpasta e mostra um resumo do que foi importado.

3. Abra o aplicativo:

   ```
   python -m streamlit run app.py
   ```

   O navegador abre em `http://localhost:8501`. Se o Streamlit pedir um e-mail no terminal, aperte Enter para pular. Para fechar o aplicativo, use Ctrl+C no terminal.

Para importar a planilha de novo do zero, apague o arquivo `dados/vendas.db` e repita o passo 2. As vendas registradas pelo aplicativo são perdidas nesse caso.

## Organização dos arquivos

```
loja-da-maria/
├── app.py              abre o aplicativo e liga as duas telas
├── migrar.py           importa a planilha antiga (roda uma vez)
├── requirements.txt    bibliotecas necessárias
├── .streamlit/
│   └── config.toml     aparência: modo claro, sem menu de desenvolvedor
├── paginas/
│   ├── registrar.py    tela do formulário
│   └── vendas.py       tela da tabela, pesquisa e correção
├── loja/
│   ├── limpeza.py      regras de limpeza, uma função por coluna
│   └── banco.py        gravar, alterar, apagar e listar vendas
├── dados/
│   └── vendas.db       onde as vendas ficam guardadas (SQLite)
└── desafio/            enunciado do desafio
```

## Tecnologias

- **Python** com **Streamlit** para as telas.
- **SQLite** para guardar as vendas em um único arquivo, sem precisar instalar um banco de dados.
- **openpyxl** e **pandas** para ler a planilha original e gerar a planilha de download.

## Limitações conhecidas

- O formulário registra apenas vendas. Devolução e compra de fornecedor não têm opção própria.
- Produtos parecidos não foram unidos (`Argola dourada` e `Brinco argola`, `Colar` e `Colar dourado`), porque não dá para saber pela planilha se são o mesmo produto.
- O aplicativo roda no computador em que foi instalado. Para a Maria usar pelo celular, seria preciso hospedá-lo e guardar os dados fora do arquivo local.
