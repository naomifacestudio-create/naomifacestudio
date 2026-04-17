/**
 * CKEditor 4 (image2): normalize alignment (block ↔ center) and lightly
 * clean pasted inline noise. Keeps class names in sync with
 * CKEDITOR_CONFIGS['image2_alignClasses'].
 */
(function () {
    'use strict';

    function whenCKEDITOR(callback) {
        if (typeof window.CKEDITOR !== 'undefined') {
            callback();
            return;
        }
        var started = Date.now();
        var timer = window.setInterval(function () {
            if (typeof window.CKEDITOR !== 'undefined') {
                window.clearInterval(timer);
                callback();
            } else if (Date.now() - started > 15000) {
                window.clearInterval(timer);
            }
        }, 50);
    }

    function patchImage2AlignField(ev) {
        if (ev.data.name !== 'image2') {
            return;
        }
        var definition = ev.data.definition;
        var info = definition.getContents('info');
        if (!info) {
            return;
        }
        var alignField = info.get('align');
        if (!alignField || !CKEDITOR.tools.isArray(alignField.items)) {
            return;
        }

        var items = alignField.items;
        var hasCenter = false;
        var i;
        var pair;
        var value;
        for (i = 0; i < items.length; i++) {
            pair = items[i];
            value = pair && (pair[1] !== undefined ? pair[1] : pair);
            if (value === 'center' || value === 'block') {
                hasCenter = true;
                break;
            }
        }
        if (!hasCenter) {
            items.push(['Center', 'center']);
        }

        var originalSetup = alignField.setup;
        alignField.setup = function (widget) {
            if (widget && widget.data && widget.data.align === 'block') {
                widget.data.align = 'center';
            }
            if (originalSetup) {
                originalSetup.call(this, widget);
            }
        };

        var originalCommit = alignField.commit;
        alignField.commit = function (widget) {
            if (this.getValue && this.getValue() === 'block' && this.setValue) {
                this.setValue('center');
            }
            if (originalCommit) {
                originalCommit.call(this, widget);
            }
            if (widget && widget.data && widget.data.align === 'block') {
                widget.setData('align', 'center');
            }
        };
    }

    function stripNoiseFromPaste(ev) {
        var editor = ev.editor;
        if (!editor || !editor.dataProcessor || !editor.dataProcessor.htmlFilter) {
            return;
        }
        if (editor._naomiRichtextPasteRules) {
            return;
        }
        editor._naomiRichtextPasteRules = true;
        editor.dataProcessor.htmlFilter.addRules({
            elements: {
                span: function (el) {
                    if (!el.attributes || !el.attributes.style) {
                        return;
                    }
                    var style = String(el.attributes.style)
                        .replace(/\s*font-family\s*:\s*[^;]+;?/gi, '')
                        .replace(/\s*font-size\s*:\s*[^;]+;?/gi, '')
                        .replace(/\s*color\s*:\s*[^;]+;?/gi, '')
                        .replace(/\s*background-color\s*:\s*[^;]+;?/gi, '')
                        .replace(/;\s*;/g, ';')
                        .trim();
                    if (!style) {
                        delete el.attributes.style;
                    } else {
                        el.attributes.style = style;
                    }
                },
            },
        });
    }

    whenCKEDITOR(function () {
        CKEDITOR.on('dialogDefinition', patchImage2AlignField);
        CKEDITOR.on('instanceReady', stripNoiseFromPaste);
    });
}());
