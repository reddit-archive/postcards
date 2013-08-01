p = {
    init: function (checkFormValid) {
        this.input = $('#username')
        this.checkFormValid = checkFormValid
        this.request = null
        this.throbber = $('<img src="//s3.amazonaws.com/redditstatic/throbber.gif">')
        this.successMark = $('<img src="//s3.amazonaws.com/redditstatic/green-check.png">')
        this.failureMark = $('<img src="//s3.amazonaws.com/redditstatic/icon-circle-exclamation.png">')

        this.input.change($.proxy(this, 'onChange'))
    },

    onChange: function () {
        if (this.request)
            return

        this.successMark.remove()
        this.failureMark.remove()

        if (!this.input.val()) {
            this.onAccountNotFound()
            return
        }

        this.input.parent().append(this.throbber)

        this.request = $.ajax({
            url: 'https://pay.reddit.com/user/' + this.input.val() + '/.json',
            dataType: 'jsonp',
            jsonp: 'jsonp',
            timeout: 5000,
        })
        this.request
            .done($.proxy(this, 'onAccountFound'))
            .fail($.proxy(this, 'onAccountNotFound'))
            .always($.proxy(this, 'onRequestFinished'))
    },

    onAccountFound: function () {
        this.input.data('valid', true)
        this.input.parent().append(this.successMark)
    },

    onAccountNotFound: function () {
        this.input.data('valid', false)
        this.input.parent().append(this.failureMark)
    },

    onRequestFinished: function () {
        this.request = null
        this.throbber.remove()
        this.checkFormValid()
    },
}

$(function() {
    var geocoder = new google.maps.Geocoder()
    var geocodeResult = undefined
    var filesUploaded = 0

    function checkFormValid() {
        var isValid = (
            $("#origin").val() == geocodeResult &&
            $("#username").data('valid') &&
            $("#date").val() != '' &&
            filesUploaded >= 1
        )

        if (isValid)
            $("#submit").removeAttr('disabled')
        else
            $("#submit").attr('disabled', '')
    }

    p.init(checkFormValid)

    $("#origin")
        .autocomplete({
            source: function(request, response) {
                geocoder.geocode({
                    address: request.term
                }, function(results, status) {
                    if (status != 'OK')
                        return

                    var autocompletion = $.map(results, function(res, i) {
                        return {
                            value: res.formatted_address,
                            result: res
                        }
                    })

                    response(autocompletion)
                })
            },

            select: function(event, ui) {
                var result = ui.item.result

                $.each(result.address_components, function(i, c) {
                    if ($.inArray("country", c.types) >= 0) {
                        $("#origin_country").val(c.short_name)
                        return false
                    }
                })

                var location = result.geometry.location
                $("#origin_latitude").val(location.lat())
                $("#origin_longitude").val(location.lng())
                $("#origin_country").val()

                geocodeResult = ui.item.value
                checkFormValid()
            }
        })

    // set up the datepicker
    $("#date").datepicker({
        changeMonth: true,
        changeYear: true,
        onSelect: function(dateText, instance) {
            checkFormValid()
        }
    })

    $("input[type=file]").change(function() {
        if (this.files.length != 1)
            return

        var reader = new FileReader()
        var xhr = new XMLHttpRequest()
        var progress = null
        var fileInput = $(this)
        var cell = fileInput.parent()

        fileInput.hide()

        xhr.upload.addEventListener("progress", function(e) {
            if (!e.lengthComputable)
                return

            if (progress === null)
                progress = $("<progress>")
                                .attr({
                                    max: e.total,
                                    value: e.loaded
                                })
                                .appendTo(cell)
            else
                progress.val(e.loaded)
        }, false)

        xhr.upload.addEventListener("load", function(e) {
            cell
                .empty()
                .text('saving to s3...')
        }, false)

        xhr.onreadystatechange = function() {
            if (xhr.readyState != 4)
                return

            cell.text('uploaded')

            $('<input>')
                .attr({
                    name: fileInput.attr('name'),
                    type: 'hidden',
                    value: xhr.responseText
                })
                .appendTo(cell)

            filesUploaded += 1
            checkFormValid()
        }

        reader.onload = function(evt) {
            xhr.send(btoa(evt.target.result))
        }

        xhr.open('POST', '/upload')
        reader.readAsBinaryString(this.files[0])
    })

    $("input")
        .keyup(checkFormValid)
        .change(checkFormValid)
    checkFormValid()
})
