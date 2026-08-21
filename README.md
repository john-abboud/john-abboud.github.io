# john-abboud.github.io

Personal GIS portfolio for **John Abboud, C.E.T.** - built while completing the Bachelor of Applied Technology, Geographic Information Systems (BGIS) program at SAIT (Calgary, AB). Live at:

**[john-abboud.github.io](https://john-abboud.github.io/)**

## What's here

A single-page site tracking coursework, tools, and project work as the program progresses - cartographic design, spatial analysis, GPS field capture, remote sensing, GIS programming, and the applied capstone project - alongside a downloadable resume and contact details.

Sections on the live site:

- **Overview** - program, background, and what I'm looking for
- **Featured work** - the completed capstone, two semester final projects, an academic poster, and the live web apps, in that order
- **Coursework** - project write-ups organized by semester and course
- **Resume** - downloadable PDF (and source Word doc)
- **Skills & tools** - software and concepts covered so far
- **Contact**

Anything already shown in full in Featured work (the capstone and the electricity-access poster, currently) is *not* duplicated below in Coursework - those course groups just link back up to Featured instead, to avoid maintaining the same write-up in two places.

## Stack

Plain HTML/CSS/JS. No build step, no framework, no bundler - just one `index.html` plus assets, served directly by GitHub Pages.

- Syntax highlighting for embedded scripts via [Prism.js](https://prismjs.com/) (loaded from cdnjs)
- Fonts via Google Fonts (Space Grotesk, Inter, JetBrains Mono)
- Scroll-triggered reveal animations and a scroll-spy nav, via vanilla `IntersectionObserver` (no library)
- Respects `prefers-reduced-motion` throughout
- Portrait-format layouts (11×17" posters) use an `img.portrait` variant (`object-fit: contain`, no cropping) instead of the default 4:3 crop; wide dashboard screenshots use an equivalent `img.contain` variant - see `.project-card img` / `.highlight-card img` in the `<style>` block if adding another oddly-shaped image
- A CSS rule auto-spans a lone leftover card across the full grid row when a course group has an odd number of cards, so nothing sits orphaned next to blank space - portrait cards are excluded from this (they'd render oversized instead), see `.project-card:last-child:nth-child(odd)`

## Repo structure

```
.
├── index.html                  # the whole site
├── images/                     # project screenshots, cover images, and poster thumbnails
│   ├── sem1-*                  # Semester 1 coursework images
│   └── sem2-*                  # Semester 2 coursework images
├── scripts/                    # downloadable source for Python/ArcPy assignments
│   ├── GEOS456_Assign01_Toulouse.py
│   ├── GEOS456_Assign02_ATS_DLS.py
│   ├── GEOS456_Assign03_SpatialDecisions.py
│   ├── GEOS456_Assign04_CrimeAnalysisTool.py
│   └── GEOS456_FinalProject_WildlifeHabitat.py
├── reports/                    # full written reports/deliverables, PDF
│   ├── sem1-geos406-solar-potential-report.pdf
│   └── sem2-geos451-devils-head-wildfire-report.pdf
├── posters/                    # full-resolution print/poster PDFs (the images/ folder holds
│   │                           # the web-sized thumbnail version of each of these)
│   ├── sem2-geos457-assignment1-california-never-married.pdf
│   ├── sem2-geos457-electricity-access-africa.pdf
│   ├── sem2-geos457-tutorial7-africa-human-development.pdf
│   └── sem2-geos459-capstone-poster.pdf
├── presentations/
│   └── sem2-geos459-capstone-presentation.pptx
└── resume/
    ├── John_Abboud_Resume.pdf  # linked from the Resume section
    └── John_Abboud_Resume.docx # source file, not linked on the site
```

Naming convention throughout: `sem{N}-{course}-{short-description}.{ext}`, e.g. `sem2-geos451-devils-head-wildfire.jpg`. Where a poster/report and its web thumbnail are a pair, they share the same base name across `images/` and `posters/`/`reports/` so it's obvious at a glance which files go together.

## Running it locally

No install, no dependencies. Either:

- Open `index.html` directly in a browser, or
- Serve the folder so relative paths behave exactly like production:

  ```bash
  python3 -m http.server 8000
  ```

  then visit `http://localhost:8000`.

## Adding a new project

1. Drop the image into `images/`, following the naming convention above. For a poster/report deliverable, also drop the full-resolution PDF into `posters/` or `reports/` under the matching base name.
   - Landscape content that's already close to 4:3 can be cropped normally.
   - Portrait layouts (11×17" posters, etc.) should **not** be cropped - use the full image and add `class="portrait"` to the `<img>` tag so it displays uncropped.
   - Unusually wide screenshots (dashboards, etc.) work the same way with `class="contain"`.
2. Find the relevant course group inside the `#coursework` section in `index.html` and copy an existing `.project-card` block as a template.
3. If it's a script-based assignment, add the `.py` file to `scripts/` and use the existing `<details class="code-toggle">` pattern to embed a collapsible, syntax-highlighted view with a download link.
4. If it belongs in **Featured work** too, add a matching `.highlight-card` at the top of the page. If it's rich enough to stand fully on its own there, consider leaving the Coursework entry as a short "featured at the top ↑" pointer instead of a full duplicate - see the GEOS 406, GEOS 457 (electricity poster), and GEOS 459 entries for the pattern.

## Updating the resume

The PDF in `resume/` is the one linked from the site - replace it directly (same filename) and the download button updates automatically. The `.docx` is kept as the editable source; re-export to PDF after making changes. The "updated" date shown next to the download button in the Resume section is set manually in `index.html` (`.rd-sub`) and needs updating by hand when the resume changes.

## Credits

- **Sanaz Ebrahimzadeh Narloo** - co-author, GEOS 406 solar potential final project
- **Delu Maduekwe** - co-cartographer, GEOS 457 electricity access poster; capstone team, GEOS 459
- **Teng Zhang** - capstone team, GEOS 459
- Client for the capstone project: CIRUS Lab, SAIT

## Contact

- Email: [john.abboud@proton.me](mailto:john.abboud@proton.me)
- LinkedIn: [linkedin.com/in/abboud-john](https://www.linkedin.com/in/abboud-john)
