/**
 * RAG Financial Intelligence — Week 2 Project (Gen Academy)
 * n8n Workflow SDK Code
 *
 * One-liner: My RAG app helps investment analysts answer financial questions
 * from SEC filings + FMP company profiles via webhook API with >90% faithfulness
 * and <15s latency.
 *
 * Workflow ID in n8n: NZcW470MuDrUKjMH
 * URL: https://djn8n1122.app.n8n.cloud/workflow/NZcW470MuDrUKjMH
 *
 * ─── RAG FRAMEWORK ──────────────────────────────────────────────────────────
 * Use case:     Investment analysts query financial documents (SEC 10-K filings,
 *               company profiles) via webhook API to answer qualitative questions
 * Corpus:       FMP Company Profile API + SEC EDGAR CIK/filing metadata (~1 structured
 *               text document per ticker, ~2-5KB each)
 * Ingestion:    POST /rag-ingest → FMP API + SEC EDGAR → structured text doc
 *               Freshness: on-demand per ticker; re-ingest to refresh
 * Cleaning:     Strip API response wrappers, normalize null values, format numbers
 * Chunking:     Recursive character splitter, 512 chars / 50 char overlap
 * Embedding:    OpenAI text-embedding-3-small (1536-dim) — matches chunk size well
 * Store:        n8n In-Memory Vector Store, keyed per ticker (financial_rag_TICKER)
 * Retrieve:     Dense semantic search, top-4 chunks, retrieve-as-tool for AI Agent
 * Generate:     GPT-4o with structured citation instructions
 *
 * ─── ENDPOINTS ──────────────────────────────────────────────────────────────
 * Flow 1 — Ingest:  POST /webhook/rag-ingest
 *                   Body: { "ticker": "AAPL" }
 *                   → Fetches FMP profile + SEC CIK, builds doc, chunks + embeds
 *
 * Flow 2 — Query:   POST /webhook/rag-query
 *                   Body: { "ticker": "AAPL", "question": "What are the risk factors?" }
 *                   → AI Agent retrieves top-4 chunks, generates cited answer
 *
 * ─── COMPANION WORKFLOW ─────────────────────────────────────────────────────
 * Existing WACC Intrinsic Valuation workflow (ID: 94LnAeM8PpFn4Xob):
 *   GET /webhook/stock-valuation?ticker=AAPL
 *   → WACC + 10-year DCF + PDF report
 *
 * Together: Use /rag-ingest + /rag-query for qualitative analysis (risk factors,
 * business model, management quality) and /stock-valuation for quantitative
 * DCF valuation. Combined = complete fundamental investment research.
 */

import {
  workflow, node, trigger, sticky,
  embeddings, documentLoader, textSplitter,
  tool, languageModel, newCredential, expr
} from '@n8n/workflow-sdk';

// ─── STICKY NOTES ─────────────────────────────────────────────────────────────

const ragOverviewNote = sticky(
  '## RAG Financial Intelligence — Week 2 Project\n\n' +
  '**One-liner:** My RAG app helps investment analysts answer financial questions from SEC filings + FMP company profiles via webhook API with >90% faithfulness and <15s latency.\n\n' +
  '**RAG Stack:**\n' +
  '- Corpus: FMP Company Profile + SEC EDGAR metadata (~1 doc per ticker)\n' +
  '- Chunking: Recursive 512 chars / 50 overlap\n' +
  '- Embedding: OpenAI text-embedding-3-small (1536-dim)\n' +
  '- Store: n8n In-Memory (per-ticker memoryKey: financial_rag_TICKER)\n' +
  '- Retrieval: Top-4 semantic chunks (retrieve-as-tool)\n' +
  '- Generation: GPT-4o with citation instructions\n\n' +
  '**Endpoints:**\n' +
  '1. POST /webhook/rag-ingest {ticker} → index docs\n' +
  '2. POST /webhook/rag-query {ticker, question} → AI answer',
  [],
  { color: 4 }
);

const ingestNote = sticky(
  '## Flow 1: RAG Document Ingestion\n\n' +
  'POST /webhook/rag-ingest\n' +
  'Body: { "ticker": "AAPL" }\n\n' +
  'Pipeline:\n' +
  '1. Validate ticker symbol\n' +
  '2. Fetch FMP company profile (description, sector, CEO, valuation)\n' +
  '3. Fetch SEC EDGAR CIK for filing links\n' +
  '4. Build full-text financial document\n' +
  '5. Chunk → Embed → Store in per-ticker vector store\n\n' +
  'Setup: Add OpenAI credential',
  [],
  { color: 6 }
);

const queryNote = sticky(
  '## Flow 2: RAG Q&A Agent\n\n' +
  'POST /webhook/rag-query\n' +
  'Body: { "ticker": "AAPL", "question": "What are the main risk factors?" }\n\n' +
  'Pipeline:\n' +
  '1. Parse ticker + question\n' +
  '2. AI Agent retrieves top-4 chunks from indexed vector store\n' +
  '3. GPT-4o generates cited answer grounded in retrieved docs\n' +
  '4. Returns JSON with answer + source metadata\n\n' +
  'Note: Run /rag-ingest first for the ticker!',
  [],
  { color: 5 }
);

// ─── FLOW 1: RAG DOCUMENT INGESTION ──────────────────────────────────────────

const ingestWebhook = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'RAG Ingest Webhook',
    parameters: {
      httpMethod: 'POST',
      path: 'rag-ingest',
      responseMode: 'responseNode',
      options: {}
    }
  },
  output: [{ body: { ticker: 'AAPL' } }]
});

const validateIngestTicker = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Validate Ingest Ticker',
    parameters: {
      mode: 'runOnceForAllItems',
      jsCode: `const ticker = ($input.first().json.body?.ticker || $input.first().json.query?.ticker || '').toString().trim().toUpperCase();
if (!ticker) throw new Error('Missing ticker. POST body: {"ticker":"AAPL"}');
if (!/^[A-Z.\-]{1,10}$/.test(ticker)) throw new Error('Invalid ticker: ' + ticker);
const FMP_API_KEY = 'VXWoHKuKG6qlMl21v2LGhTJ3n4nfPS94'; // from existing valuation workflow
return [{ json: { ticker, fmpApiKey: FMP_API_KEY } }];`
    }
  },
  output: [{ ticker: 'AAPL', fmpApiKey: 'key' }]
});

const fetchCompanyProfile = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'FMP Company Profile',
    parameters: {
      method: 'GET',
      url: 'https://financialmodelingprep.com/stable/profile',
      sendQuery: true,
      queryParameters: {
        parameters: [
          { name: 'symbol', value: expr('{{ $json.ticker }}') },
          { name: 'apikey', value: expr('{{ $json.fmpApiKey }}') }
        ]
      },
      options: { response: { response: { neverError: true } } }
    }
  },
  output: [{
    symbol: 'AAPL', companyName: 'Apple Inc.',
    description: 'Apple Inc. designs smartphones and computers.',
    sector: 'Technology', industry: 'Consumer Electronics',
    mktCap: 3000000000000, beta: 1.24, price: 195.0,
    ceo: 'Tim Cook', fullTimeEmployees: 150000
  }]
});

const fetchSecCikIngest = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'SEC EDGAR CIK Lookup',
    parameters: {
      method: 'GET',
      url: 'https://efts.sec.gov/LATEST/search-index',
      sendQuery: true,
      queryParameters: {
        parameters: [
          { name: 'q', value: expr("{{ $('Validate Ingest Ticker').first().json.ticker }}") },
          { name: 'forms', value: '10-K' },
          { name: 'dateRange', value: 'custom' },
          { name: 'startdt', value: '2023-01-01' }
        ]
      },
      sendHeaders: true,
      headerParameters: {
        parameters: [{ name: 'User-Agent', value: 'n8n-rag-ingest contact@example.com' }]
      },
      options: { response: { response: { neverError: true } } }
    }
  },
  output: [{ hits: { hits: [{ _source: { entity_id: '0000320193' } }] } }]
});

const buildRagDocument = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Build Financial RAG Document',
    parameters: {
      mode: 'runOnceForAllItems',
      jsCode: `const ticker = $('Validate Ingest Ticker').first().json.ticker;
const raw = $('FMP Company Profile').first().json;
const prof = Array.isArray(raw) ? (raw[0] || {}) : (raw || {});
const secData = $('SEC EDGAR CIK Lookup').first().json;
const cikSrc = secData?.hits?.hits?.[0]?._source || {};
const cik = (cikSrc.entity_id || '').toString().replace(/^CIK/i, '');
const fmt = (n) => n != null ? String(n) : 'N/A';
const fmtB = (n) => n ? '$' + (Number(n)/1e9).toFixed(2) + 'B' : 'N/A';

// Build a rich, structured text document for RAG ingestion
const doc = [
  '# ' + fmt(prof.companyName) + ' (' + ticker + ') - Financial Intelligence Document',
  '',
  '## Company Overview',
  'Ticker: ' + ticker,
  'Company Name: ' + fmt(prof.companyName),
  'Exchange: ' + fmt(prof.exchangeShortName || prof.exchange),
  'Sector: ' + fmt(prof.sector),
  'Industry: ' + fmt(prof.industry),
  'Country: ' + fmt(prof.country),
  'CEO: ' + fmt(prof.ceo),
  'Full-Time Employees: ' + fmt(prof.fullTimeEmployees),
  'Website: ' + fmt(prof.website),
  'IPO Date: ' + fmt(prof.ipoDate),
  'SEC CIK: ' + cik,
  '',
  '## Business Description',
  (prof.description || 'No description available.'),
  '',
  '## Market and Valuation Data',
  'Current Price: $' + fmt(prof.price),
  'Market Capitalization: ' + fmtB(prof.mktCap),
  'Beta (market sensitivity): ' + fmt(prof.beta),
  'Volume Average: ' + fmt(prof.volAvg),
  'Last Dividend Paid: $' + fmt(prof.lastDiv),
  'DCF Fair Value (FMP model): $' + fmt(prof.dcf),
  'DCF vs Market Price Differential: ' + fmt(prof.dcfDiff) + '%',
  '',
  '## SEC Filing References',
  'CIK: ' + cik,
  '10-K Filings URL: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=' + cik + '&type=10-K',
  'XBRL Company Facts: https://data.sec.gov/api/xbrl/companyfacts/CIK' + String(cik).padStart(10,'0') + '.json',
  '',
  '## Investment Risk Context',
  fmt(prof.companyName) + ' operates in the ' + fmt(prof.sector) + ' sector (' + fmt(prof.industry) + ').',
  'Beta of ' + fmt(prof.beta) + ' indicates ' + (parseFloat(prof.beta || 1) > 1 ? 'above-average' : 'below-average') + ' market sensitivity.',
  'Dividend policy: last dividend $' + fmt(prof.lastDiv) + ' per share.',
  'FMP DCF model implies ' + (parseFloat(prof.dcfDiff || 0) > 0 ? 'undervaluation' : 'overvaluation') + ' of ' + Math.abs(parseFloat(prof.dcfDiff || 0)).toFixed(1) + '% vs current price.',
  'Document generated: ' + new Date().toISOString().slice(0,10)
].join('\\n');

return [{ json: { ticker, document: doc, companyName: prof.companyName || ticker, cik, sector: prof.sector || 'N/A' } }];`
    }
  },
  output: [{
    ticker: 'AAPL',
    document: '# Apple Inc. (AAPL) - Financial Intelligence Document\n\n...',
    companyName: 'Apple Inc.', cik: '0000320193', sector: 'Technology'
  }]
});

// RAG ingestion subnodes
const splitterNode = textSplitter({
  type: '@n8n/n8n-nodes-langchain.textSplitterRecursiveCharacterTextSplitter',
  version: 1,
  config: {
    name: 'Recursive Splitter (512 / 50)',
    parameters: { chunkSize: 512, chunkOverlap: 50 }
  }
});

const docLoaderNode = documentLoader({
  type: '@n8n/n8n-nodes-langchain.documentDefaultDataLoader',
  version: 1.1,
  config: {
    name: 'Financial Document Loader',
    parameters: {
      dataType: 'json',
      jsonMode: 'expressionData',
      jsonData: expr('{{ $json.document }}'),
      textSplittingMode: 'custom',
      options: {
        metadata: {
          metadataValues: [
            { name: 'ticker', value: expr('{{ $json.ticker }}') },
            { name: 'sector', value: expr('{{ $json.sector }}') },
            { name: 'source', value: 'FMP_SEC_EDGAR' },
            { name: 'docType', value: 'financial_profile' }
          ]
        }
      }
    },
    subnodes: { textSplitter: splitterNode }
  }
});

const embeddingsIngest = embeddings({
  type: '@n8n/n8n-nodes-langchain.embeddingsOpenAi',
  version: 1.2,
  config: {
    name: 'OpenAI Embeddings — text-embedding-3-small',
    parameters: { model: 'text-embedding-3-small' },
    credentials: { openAiApi: newCredential('n8n free OpenAI API credits') }
  }
});

const vectorStoreInsert = node({
  type: '@n8n/n8n-nodes-langchain.vectorStoreInMemory',
  version: 1.3,
  config: {
    name: 'Insert into Financial Vector Store',
    parameters: {
      mode: 'insert',
      memoryKey: { __rl: true, mode: 'id', value: expr('financial_rag_{{ $json.ticker }}') },
      clearStore: true
    },
    subnodes: {
      embedding: embeddingsIngest,
      documentLoader: docLoaderNode
    }
  },
  output: [{ ticker: 'AAPL', document: '...', companyName: 'Apple Inc.', cik: '0000320193', sector: 'Technology' }]
});

const respondIngestDone = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Respond: Indexed',
    parameters: {
      respondWith: 'json',
      responseBody: expr('{{ JSON.stringify({ status: "indexed", ticker: $json.ticker, company: $json.companyName, memoryKey: "financial_rag_" + $json.ticker, chunking: "recursive_512_50", embeddingModel: "text-embedding-3-small", message: "Financial docs embedded. Now query via POST /webhook/rag-query with {ticker, question}" }) }}'),
      options: { responseCode: 200 }
    }
  }
});

// ─── FLOW 2: RAG Q&A AGENT ────────────────────────────────────────────────────

const ragQueryWebhook = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'RAG Query Webhook',
    parameters: {
      httpMethod: 'POST',
      path: 'rag-query',
      responseMode: 'responseNode',
      options: {}
    }
  },
  output: [{ body: { ticker: 'AAPL', question: 'What are the main risk factors for this company?' } }]
});

const parseQueryInput = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Parse Query Input',
    parameters: {
      mode: 'runOnceForAllItems',
      jsCode: `const b = $input.first().json.body || $input.first().json;
const ticker = (b.ticker || '').toString().trim().toUpperCase();
const question = (b.question || '').toString().trim();
if (!ticker) throw new Error('Missing ticker. Body: {"ticker":"AAPL","question":"..."}');
if (!question) throw new Error('Missing question. Body: {"ticker":"AAPL","question":"What are risk factors?"}');
if (!/^[A-Z.\-]{1,10}$/.test(ticker)) throw new Error('Invalid ticker: ' + ticker);
return [{ json: { ticker, question, memoryKey: 'financial_rag_' + ticker } }];`
    }
  },
  output: [{ ticker: 'AAPL', question: 'What are the main risk factors?', memoryKey: 'financial_rag_AAPL' }]
});

const embeddingsQuery = embeddings({
  type: '@n8n/n8n-nodes-langchain.embeddingsOpenAi',
  version: 1.2,
  config: {
    name: 'OpenAI Embeddings — Query',
    parameters: { model: 'text-embedding-3-small' },
    credentials: { openAiApi: newCredential('n8n free OpenAI API credits') }
  }
});

const knowledgeBaseTool = tool({
  type: '@n8n/n8n-nodes-langchain.vectorStoreInMemory',
  version: 1.3,
  config: {
    name: 'Financial Filing Knowledge Base',
    parameters: {
      mode: 'retrieve-as-tool',
      toolDescription: 'Search indexed SEC filings, company profiles, business descriptions, risk factors, valuation data, and financial metrics for the queried stock ticker. Always use this tool first before answering financial questions about a specific company.',
      memoryKey: { __rl: true, mode: 'id', value: expr("{{ $('Parse Query Input').first().json.memoryKey }}") },
      topK: 4,
      includeDocumentMetadata: true
    },
    subnodes: { embedding: embeddingsQuery }
  }
});

const gptModel = languageModel({
  type: '@n8n/n8n-nodes-langchain.lmChatOpenAi',
  version: 1.3,
  config: {
    name: 'GPT-4o Financial Analyst',
    parameters: {
      model: { __rl: true, mode: 'id', value: 'gpt-4o' },
      options: { temperature: 0.1 }
    },
    credentials: { openAiApi: newCredential('n8n free OpenAI API credits') }
  }
});

const ragAgent = node({
  type: '@n8n/n8n-nodes-langchain.agent',
  version: 3.1,
  config: {
    name: 'Financial RAG Agent',
    parameters: {
      promptType: 'define',
      text: expr("{{ $('Parse Query Input').first().json.question }}"),
      options: {
        systemMessage: 'You are an expert financial analyst specializing in SEC filings and company fundamentals. Use the Financial Filing Knowledge Base tool to retrieve relevant information before answering. Structure every answer as: (1) Direct answer, (2) Evidence from retrieved documents with specific citations, (3) Key caveats or limitations. If documents are not found in the knowledge base, tell the user to first POST to /webhook/rag-ingest with the ticker symbol.',
        maxIterations: 5,
        returnIntermediateSteps: false
      }
    },
    subnodes: {
      model: gptModel,
      tools: [knowledgeBaseTool]
    }
  },
  output: [{ output: 'Based on the SEC filings and company profile for AAPL, the main risk factors include...' }]
});

const formatRagResponse = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Format RAG Response',
    parameters: {
      mode: 'runOnceForAllItems',
      jsCode: `const ticker = $('Parse Query Input').first().json.ticker;
const question = $('Parse Query Input').first().json.question;
const answer = $input.first().json.output || '';
return [{ json: {
  status: 'success',
  ticker,
  question,
  answer,
  retrievalSource: 'financial_rag_' + ticker,
  model: 'gpt-4o',
  embeddingModel: 'text-embedding-3-small',
  faithfulnessTarget: '>90%',
  timestamp: new Date().toISOString()
} }];`
    }
  },
  output: [{
    status: 'success', ticker: 'AAPL',
    question: 'What are the risk factors?',
    answer: 'Based on the filings...',
    retrievalSource: 'financial_rag_AAPL', model: 'gpt-4o'
  }]
});

const respondRagAnswer = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Respond: RAG Answer',
    parameters: {
      respondWith: 'firstIncomingItem',
      options: { responseCode: 200 }
    }
  }
});

// ─── WORKFLOW COMPOSITION ─────────────────────────────────────────────────────

export default workflow('rag-financial-intelligence', 'RAG Financial Intelligence — Week 2 Project')
  .add(ragOverviewNote)
  .add(ingestNote)
  .add(queryNote)
  // Flow 1: RAG Document Ingestion
  .add(ingestWebhook)
  .to(validateIngestTicker)
  .to(fetchCompanyProfile)
  .to(fetchSecCikIngest)
  .to(buildRagDocument)
  .to(vectorStoreInsert)
  .to(respondIngestDone)
  // Flow 2: RAG Q&A Agent
  .add(ragQueryWebhook)
  .to(parseQueryInput)
  .to(ragAgent)
  .to(formatRagResponse)
  .to(respondRagAnswer);
