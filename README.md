# john-abboud.github.io

Personal GIS portfolio for **John Abboud, C.E.T.** - built while completing the Bachelor of Applied Technology, Geographic Information Systems (BGIS) program at SAIT (Calgary, AB). Live at:

**[john-abboud.github.io](https://john-abboud.github.io/)**

## What's here

A single-page site tracking coursework, tools, and project work as the program progresses - cartographic design, spatial analysis, GPS field capture, remote sensing, GIS programming, and the applied capstone project - alongside a downloadable resume and contact details.

Sections on the live site:

- **Overview** - program, background, and what I'm looking for
- **Featured work** - the capstone project, live web apps, and the Semester 1 story map
- **Coursework** - project write-ups organized by semester and course
- **Resume** - downloadable PDF (and source Word doc)
- **Skills & tools** - software and concepts covered so far
- **Contact**

## Stack

Plain HTML/CSS/JS. No build step, no framework, no bundler - just one `index.html` plus assets, served directly by GitHub Pages.

- Syntax highlighting for embedded scripts via [Prism.js](https://prismjs.com/) (loaded from cdnjs)
- Fonts via Google Fonts (Space Grotesk, Inter, JetBrains Mono)
- Scroll-triggered reveal animations and a scroll-spy nav, via vanilla `IntersectionObserver` (no library)
- Respects `prefers-reduced-motion` throughout

## Repo structure

```
.
├── index.html                  # the whole site
├── images/                     # project screenshots and cover images
│   ├── sem1-*                  # Semester 1 coursework images
│   └── sem2-*                  # Semester 2 coursework images
├── scripts/                    # downloadable source for Python/ArcPy assignments
│   ├── GEOS456_Assign01_Toulouse.py
│   └── GEOS456_Assign02_ATS_DLS.py
└── resume/
    ├── John_Abboud_Resume.pdf  # linked from the Resume section
    └── John_Abboud_Resume.docx # source file, not linked on the site
```

## Running it locally

No install, no dependencies. Either:

- Open `index.html` directly in a browser, or
- Serve the folder so relative paths behave exactly like production:

  ```bash
  python3 -m http.server 8000
  ```

  then visit `http://localhost:8000`.

## Adding a new project

1. Drop the image into `images/`, following the existing naming convention: `sem{N}-{course}-{short-description}.jpg`.
2. Find the relevant course group inside the `#coursework` section in `index.html` and copy an existing `.project-card` block as a template.
3. If it's a script-based assignment, add the `.py` file to `scripts/` and use the existing `<details class="code-toggle">` pattern to embed a collapsible, syntax-highlighted view with a download link.
4. If it belongs in **Featured work** too, add a matching `.highlight-card` at the top of the page.

## Updating the resume

The PDF in `resume/` is the one linked from the site - replace it directly (same filename) and the download button updates automatically. The `.docx` is kept as the editable source; re-export to PDF after making changes.

## Credits

- **Sanaz Ebrahimzadeh Narloo** - co-author, GEOS 406 solar potential story map
- **Delu Maduekwe** and **Teng Zhang** - capstone team, GEOS 459
- Client for the capstone project: CIRUS Lab, SAIT

## Contact

- Email: [john.abboud@proton.me](mailto:john.abboud@proton.me)
- LinkedIn: [linkedin.com/in/abboud-john](https://www.linkedin.com/in/abboud-john)
