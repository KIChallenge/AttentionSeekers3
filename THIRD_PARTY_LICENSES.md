# Third-party licences

Generated from the installed package metadata (`requirements.txt`, `web/package.json`). All dependencies are used unmodified.

## Styling and data

| Component | Licence | Note |
| --- | --- | --- |
| medlyn UI styling (`web/app/globals.css`, `web/components/ui/*`) – github.com/Julian-AT/medlyn | CC BY-NC 4.0 | used with the author's permission for this challenge, non-commercial; commercial use needs a separate licence (see `web/NOTICE.md`) |
| Regional classifications (`klassifikationen/regionen/`) | CC BY 4.0 | Quelle: Statistik Austria |
| Package data (deliveries, pensions, templates) | – | synthetic, provided publicly via the SV-BOX by the Dachverband |
| PostgreSQL 16 | PostgreSQL License | local database server (not redistributed) |

## Python (`requirements.txt`)

| Package | Version | Licence |
| --- | --- | --- |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| cloudpickle | 3.1.2 | BSD License |
| colorama | 0.4.6 | BSD License |
| contourpy | 1.3.2 | BSD License |
| cycler | 0.12.1 | BSD License |
| defusedxml | 0.7.1 | Python Software Foundation License |
| et_xmlfile | 2.0.0 | MIT License |
| exceptiongroup | 1.3.1 | MIT License |
| fastapi | 0.162.0 | MIT |
| fonttools | 4.65.0 | MIT |
| h11 | 0.16.0 | MIT License |
| httpcore2 | 2.14.0 | BSD-3-Clause |
| httpx2 | 2.14.0 | BSD-3-Clause |
| idna | 3.20 | BSD-3-Clause |
| iniconfig | 2.3.1 | MIT |
| Jinja2 | 3.1.6 | BSD License |
| jiter | 0.18.0 | MIT |
| joblib | 1.6.0 | BSD-3-Clause |
| kiwisolver | 1.5.1 | BSD License |
| markdown-it-py | 4.2.0 | MIT License |
| MarkupSafe | 3.0.4 | BSD-3-Clause |
| matplotlib | 3.10.9 | Python Software Foundation License |
| mdurl | 0.1.2 | MIT License |
| numpy | 2.2.6 | BSD License |
| odfpy | 1.4.1 | Apache Software License; GNU General Public License (GPL); GNU Library or Lesser General Public License (LGPL) |
| openai | 3.41.0 | Apache-2.0 |
| openpyxl | 3.1.5 | MIT License |
| opentelemetry-api | 1.45.1 | Apache-2.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pandas | 2.3.3 | BSD License |
| pillow | 12.3.0 | MIT-CMU |
| pluggy | 1.7.0 | MIT License |
| psycopg | 3.3.6 | LGPL-3.0-only |
| psycopg-binary | 3.3.6 | LGPL-3.0-only |
| pydantic | 2.14.1 | MIT |
| pydantic_core | 2.50.1 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| pyparsing | 3.3.3 | MIT |
| pypdf | 6.21.4 | BSD-3-Clause |
| pytest | 8.4.2 | MIT License |
| python-dateutil | 3.0.0 | BSD License; Apache Software License |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| pytz | 2026.5 | MIT License |
| rich | 15.0.0 | MIT License |
| scikit-learn | 1.7.2 | BSD-3-Clause |
| scipy | 1.15.3 | BSD License |
| seaborn | 0.13.2 | BSD License |
| shellingham | 1.5.4 | ISC License (ISCL) |
| six | 1.17.0 | MIT License |
| sniffio | 1.3.1 | MIT License; Apache Software License |
| starlette | 1.7.0 | BSD-3-Clause |
| threadpoolctl | 3.7.0 | BSD-3-Clause |
| tomli | 2.5.0 | MIT |
| truststore | 0.10.5 | MIT |
| typer | 0.27.3 | MIT |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| tzdata | 2026.6 | Apache-2.0 |
| uvicorn | 0.54.0 | BSD-3-Clause |

odfpy is triple-licensed (Apache-2.0 / GPL / LGPL); we use it under Apache-2.0. psycopg is LGPL-3.0: used as an unmodified library dependency (dynamic import), which the LGPL permits; a permissive alternative would be pg8000.

## Web (`web/package.json`)

| Package | Version | Licence | |
| --- | --- | --- | --- |
| @fontsource-variable/inter | 5.3.0 | OFL-1.1 |  |
| @hugeicons/core-free-icons | 4.4.0 | MIT |  |
| @hugeicons/react | 1.1.10 | MIT |  |
| @xyflow/react | 12.12.0 | MIT |  |
| class-variance-authority | 0.7.1 | Apache-2.0 |  |
| clsx | 2.1.1 | MIT |  |
| cmdk | 1.1.1 | MIT |  |
| geist | 1.8.2 | SIL OPEN FONT LICENSE |  |
| motion | 14.7.1 | MIT |  |
| next | 16.4.3 | MIT |  |
| next-themes | 0.4.6 | MIT |  |
| radix-ui | 1.8.1 | MIT |  |
| react | 19.3.1 | MIT |  |
| react-dom | 19.3.1 | MIT |  |
| recharts | 3.8.0 | MIT |  |
| shadcn | 4.23.0 | MIT |  |
| shiki | 4.5.0 | MIT |  |
| sonner | 2.0.8 | MIT |  |
| streamdown | 2.7.1 | Apache-2.0 |  |
| tailwind-merge | 3.7.0 | MIT |  |
| tw-animate-css | 1.4.0 | MIT |  |
| vaul | 1.1.2 | MIT |  |
| @tailwindcss/postcss | 4.3.3 | MIT | dev |
| @types/node | 24.19.2 | MIT | dev |
| @types/react | 19.3.0 | MIT | dev |
| @types/react-dom | 19.3.0 | MIT | dev |
| tailwindcss | 4.3.3 | MIT | dev |
| typescript | 5.9.3 | Apache-2.0 | dev |
