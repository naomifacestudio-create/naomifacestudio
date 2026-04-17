/**
 * CKEditor 4 (image2): normalize alignment (toolbar "justify block" uses align
 * 'block', which image2_alignClasses does not map — treat as center). DOM fix
 * clears leftover float:left on img. Class names match CKEDITOR_CONFIGS image2_alignClasses.
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

    /**
     * image2 maps toolbar "justify block" to align === 'block', but image2_alignClasses
     * only defines left/center/right indices — 'block' is not mapped and often renders like left.
     * Normalize to 'center' whenever the image widget data changes.
     */
    function coerceImage2BlockAlignToCenter(ev) {
        var editor = ev.editor;
        editor.widgets.on('instanceCreated', function (evt) {
            var widget = evt.data;
            if (!widget || widget.name !== 'image') {
                return;
            }
            widget.on('data', function () {
                var a = widget.data.align;
                if (a === 'block') {
                    CKEDITOR.tools.setTimeout(function () {
                        if (widget.data.align === 'block') {
                            widget.setData('align', 'center');
                        }
                        applyImage2CenterDomFix(widget);
                    }, 0);
                    return;
                }
                if (a === 'center') {
                    CKEDITOR.tools.setTimeout(function () {
                        applyImage2CenterDomFix(widget);
                    }, 0);
                }
            });
        });
    }

    function applyImage2CenterDomFix(widget) {
        if (!widget || widget.name !== 'image' || !widget.parts || !widget.parts.image) {
            return;
        }
        var align = widget.data.align;
        if (align === 'block') {
            align = 'center';
        }
        if (align !== 'center') {
            return;
        }
        var img = widget.parts.image;
        var wrap = widget.wrapper;
        var classes = [
            'image-align-left',
            'image-align-center',
            'image-align-right',
        ];
        var i;
        for (i = 0; i < classes.length; i++) {
            wrap.removeClass(classes[i]);
            img.removeClass(classes[i]);
        }
        wrap.addClass('image-align-center');
        img.addClass('image-align-center');
        img.removeAttribute('align');
        img.removeStyle('float');
        img.removeStyle('margin-left');
        img.removeStyle('margin-right');
        img.setStyle('display', 'block');
        img.setStyle('margin-left', 'auto');
        img.setStyle('margin-right', 'auto');
        img.setStyle('float', 'none');
        wrap.removeStyle('float');
        wrap.setStyle('text-align', 'center');
        wrap.setStyle('float', 'none');
    }

    /**
     * After image2 dialog OK: defer so widget.data reflects the dialog commit (toolbar
     * "justify center" can set align to 'block' before coercion runs).
     */
    function patchImage2CenterOnDialogOk(ev) {
        var editor = ev.editor;
        editor.on('dialogShow', function (evt) {
            var dialog = evt.data;
            if (!dialog || dialog.getName() !== 'image2') {
                return;
            }
            dialog.once(
                'ok',
                function () {
                    var ed = dialog.getParentEditor();
                    CKEDITOR.tools.setTimeout(function () {
                        var w = ed.widgets.focused;
                        if (!w || w.name !== 'image') {
                            w =
                                typeof dialog.getModel === 'function'
                                    ? dialog.getModel()
                                    : null;
                        }
                        applyImage2CenterDomFix(w);
                    }, 0);
                },
                null,
                null,
                999
            );
        });
    }

    whenCKEDITOR(function () {
        CKEDITOR.on('dialogDefinition', patchImage2AlignField);
        CKEDITOR.on('instanceReady', function (ev) {
            coerceImage2BlockAlignToCenter(ev);
            patchImage2CenterOnDialogOk(ev);
        });
    });
}());
