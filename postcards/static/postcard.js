$(function() {
    var geocoder = new google.maps.Geocoder()
    var geocodeResult = undefined
    var filesUploaded = 0

    function checkFormValid() {
        var isValid = (
            $("#origin").val() == geocodeResult &&
            $("#username").val() != '' &&
            $("#date").val() != '' &&
            filesUploaded == 1
        )

        if (isValid)
            $("#submit").removeAttr('disabled')
        else
            $("#submit").attr('disabled', '')
    }

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
