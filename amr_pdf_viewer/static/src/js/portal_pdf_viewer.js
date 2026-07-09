odoo.define("amr_pdf_viewer.portal_pdf_viewer", function (require) {
"use strict";

var publicWidget = require("web.public.widget");

// Pastikan pdf.min.js sudah dimuat terlebih dahulu
var pdfjsLib = window.pdfjsLib || window["pdfjs-dist/build/pdf"];

if (!pdfjsLib) {
    console.error("PDF.js not loaded");
    return;
}

pdfjsLib.GlobalWorkerOptions.workerSrc =
    "/amr_pdf_viewer/static/src/lib/pdfjs/pdf.worker.min.js";


publicWidget.registry.AmrPdfViewer = publicWidget.Widget.extend({

    selector: ".amr_pdf",

    start: function () {

        var self = this;

        this.url = this.el.dataset.url;

        this.pageNumber = parseInt(
            this.el.dataset.page || "1",
            10
        );

        this.scale = parseFloat(
            this.el.dataset.scale || "1.2"
        );

        this.pdf = null;

        this.canvas = null;

        this.ctx = null;

        this._buildLayout();

        this._bindEvents();

        return this._super.apply(this, arguments)
            .then(function () {
                return self._loadPdf();
            });

    },


    //-----------------------------------------------------
    // UI
    //-----------------------------------------------------

    _buildLayout: function () {

        this.el.innerHTML = `
            <div class="amr_pdf_toolbar">

                <button type="button" class="btn btn-secondary btn-sm btn-prev">
                    ◀
                </button>

                <span class="page-info">
                    1 / 1
                </span>

                <button type="button" class="btn btn-secondary btn-sm btn-next">
                    ▶
                </button>

                <div style="flex:1"></div>

                <button type="button" class="btn btn-secondary btn-sm btn-zoom-out">
                    −
                </button>

                <span class="zoom-info">
                    100%
                </span>

                <button type="button" class="btn btn-secondary btn-sm btn-zoom-in">
                    +
                </button>

            </div>

            <div class="amr_pdf_container">

                <canvas></canvas>

            </div>
        `;

        this.canvas = this.el.querySelector("canvas");

        this.ctx = this.canvas.getContext("2d");

    },


    _bindEvents: function () {

        var self = this;

        this.el.querySelector(".btn-prev")
            .addEventListener("click", function () {
                self.prevPage();
            });

        this.el.querySelector(".btn-next")
            .addEventListener("click", function () {
                self.nextPage();
            });

        this.el.querySelector(".btn-zoom-in")
            .addEventListener("click", function () {
                self.zoomIn();
            });

        this.el.querySelector(".btn-zoom-out")
            .addEventListener("click", function () {
                self.zoomOut();
            });

    },


    //-----------------------------------------------------
    // PDF
    //-----------------------------------------------------

    _loadPdf: function () {

        var self = this;

        return pdfjsLib
            .getDocument(this.url)
            .promise
            .then(function (pdf) {

                self.pdf = pdf;

                if (self.pageNumber > pdf.numPages) {
                    self.pageNumber = pdf.numPages;
                }

                return self.renderPage();

            })
            .catch(function (err) {

                console.error(err);

                self.el.innerHTML =
                    "<div class='alert alert-danger'>Unable to load PDF.</div>";

            });

    },


    renderPage: function () {

        var self = this;

        return this.pdf
            .getPage(this.pageNumber)
            .then(function (page) {

                var viewport = page.getViewport({
                    scale: self.scale
                });

                self.canvas.width = viewport.width;
                self.canvas.height = viewport.height;

                return page.render({

                    canvasContext: self.ctx,

                    viewport: viewport

                }).promise;

            })
            .then(function () {

                self._refreshToolbar();

            });

    },


    //-----------------------------------------------------
    // Toolbar
    //-----------------------------------------------------

    _refreshToolbar: function () {

        this.el.querySelector(".page-info").textContent =
            this.pageNumber + " / " + this.pdf.numPages;

        this.el.querySelector(".zoom-info").textContent =
            Math.round(this.scale * 100) + "%";

    },


    //-----------------------------------------------------
    // Navigation
    //-----------------------------------------------------

    nextPage: function () {

        if (!this.pdf)
            return;

        if (this.pageNumber >= this.pdf.numPages)
            return;

        this.pageNumber++;

        return this.renderPage();

    },


    prevPage: function () {

        if (!this.pdf)
            return;

        if (this.pageNumber <= 1)
            return;

        this.pageNumber--;

        return this.renderPage();

    },


    //-----------------------------------------------------
    // Zoom
    //-----------------------------------------------------

    zoomIn: function () {

        this.scale += 0.25;

        return this.renderPage();

    },


    zoomOut: function () {

        if (this.scale <= 0.50)
            return;

        this.scale -= 0.25;

        return this.renderPage();

    },

});

});