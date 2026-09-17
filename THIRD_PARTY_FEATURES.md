# Third-Party Features and License Attribution
**Project**: JARVIS  
**Developer**: Vamshi Krishna  
**Date**: September 2026  

---

## Overview
JARVIS incorporates selected modules, architectural patterns, and utilities from open-source repositories located in `C:\Jarvis\integrations\`. In accordance with open-source licensing compliance and project integrity standards:
- All source code is credited to its respective authors.
- Compatible permissive licenses (MIT, Apache 2.0) are respected and attributed.
- Non-commercial and copyleft licenses (AdvancedJarvis Custom Non-Commercial, Agent Zero GPL-3.0) are strictly treated as conceptual/architectural references; **no direct code is copied** to avoid licensing contamination.
- JARVIS remains the sovereign, primary application.

---

## Attribution Matrix

| Repository | Source URL | Upstream License | Features Used | Files Imported / Adapted | Attribution & Compliance Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **win-computer-use** / **WindowsComputerUse** | [CarlosShao/win-computer-use](https://github.com/CarlosShao/win-computer-use) | MIT License (Copyright (c) 2026 CarlosShao) | Windows UI automation, window management, screen capture, bounding checks, failsafe abort, Windows OCR | Adapted into `backend/modules/computer/` (`safety.py`, `screen.py`, `window_mgmt.py`, `input_control.py`, `ocr_util.py`) | **Compliant** (MIT notice preserved) |
| **WindowsJarvis** | [ndunl075/Jarvis](https://github.com/ndunl075/Jarvis) | MIT License (Copyright (c) 2026 Jarvis Contributors) | Audio barge-in / stop detection, screen vision analysis with Ollama, system performance stats, app control | Adapted into `backend/modules/voice/`, `backend/modules/vision/`, `backend/modules/computer/` | **Compliant** (MIT notice preserved) |
| **AdvancedJarvis** | [isair/jarvis](https://github.com/isair/jarvis) | Custom Non-Commercial (Copyright (c) 2025 Baris Sencan) | Persistent memory concepts, semantic recall gating, sensitive credential redaction patterns | Clean-room re-implementation in `backend/modules/memory/` and `backend/modules/core/security.py` | **Clean-Room Adapted** (No code copied; conceptual reference only) |
| **OfflineJarvis** | [Ambidiosidad/jarvis](https://github.com/Ambidiosidad/jarvis) | Apache License 2.0 (Copyright (c) 2024 Ambidiosidad) | Semantic memory relationships, memory deduplication, modular service boundaries | Adapted into `backend/modules/memory/` | **Compliant** (Apache 2.0 notice preserved) |
| **PDF-RAG** (rag-ollama) | [techanvconsulting/rag-ollama](https://github.com/techanvconsulting/rag-ollama) | MIT License | PDF text extraction, document hash deduplication, FAISS vector store indexing | Adapted into `backend/modules/rag/` (`pdf_loader.py`, `rag_store.py`, `build_index.py`) | **Compliant** (MIT notice preserved) |
| **RAG-FromScratch** | [tajwarchy/rag-from-scratch](https://github.com/tajwarchy/rag-from-scratch) | MIT License (Copyright (c) 2026 Tajwar) | FastAPI RAG endpoints, chunk metadata with source/page citations, test patterns | Adapted into `backend/modules/rag/` and `backend/main.py` | **Compliant** (MIT notice preserved) |
| **ChatPDF** | [Abdelrahman-Atef-Elsayed/ChatPDF](https://github.com/Abdelrahman-Atef-Elsayed/ChatPDF) | MIT License (Copyright (c) 2024 Abdelrahman Atef) | Multi-format chunking, hybrid retrieval concepts, citation formatting | Adapted into `backend/modules/rag/` | **Compliant** (MIT notice preserved) |
| **PanPenek/JarvisAi** | [PanPenek/JarvisAi](https://github.com/PanPenek/JarvisAi) | MIT License | Desktop interaction helpers, status event broadcasts | Adapted into `backend/modules/computer/` | **Compliant** (MIT notice preserved) |
| **ARIA** | [SpandanNagale/ARIA](https://github.com/SpandanNagale/ARIA) | MIT License | Assistant tool-calling conventions, Windows productivity commands | Adapted into `backend/modules/agents/` | **Compliant** (MIT notice preserved) |
| **Agent Zero** | [thefilesareinthecomputer/agent-zero](https://github.com/thefilesareinthecomputer/agent-zero) | GNU General Public License v3.0 | Agent loop structure, context window compaction | **None** (Architecture studied only; zero code copied to prevent GPL copyleft) | **Compliant** (Zero GPL code in JARVIS) |

---

## Detailed License Texts

### 1. win-computer-use (MIT)
```text
MIT License

Copyright (c) 2026 CarlosShao

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

### 2. WindowsJarvis (MIT)
```text
MIT License

Copyright (c) 2026 Jarvis Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

### 3. RAG-FromScratch (MIT)
```text
MIT License

Copyright (c) 2026 Tajwar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

### 4. OfflineJarvis (Apache 2.0)
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
