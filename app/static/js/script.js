let protocol = (location.hostname === "localhost" || location.hostname === "127.0.0.1") ? "http" : "https";
let socket = io.connect(protocol + '://' + document.domain + ':' + location.port);

socket.on('connect', function() {
    console.log('Connected to the server');
});

socket.on('new_event', function(event) {
$('#events').prepend('<p>' + event.msg + '</p>');
    if ($('#events').children().length > 1000) {
        $('#events').children().last().remove();
    }
});

// This function tries to parse a string to Date, and if it succeeds, it returns the Date, otherwise, the original string.
function parseISODate(isoString) {
    const regexDate = /^\d{4}-\d{2}-\d{2}$/;
    const regexDateTime = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;
    if (regexDate.test(isoString) || regexDateTime.test(isoString)) {
        return new Date(isoString);
    } else {
        return isoString;
    }
}

let dataAccumulated = [];
let headersReceived = false;
let headers = [];

socket.on('pivot_data', function(event) {
    if (event.start) {
      dataAccumulated = [];
      headersReceived = false;
    }
    if (event.headers && !headersReceived) {
      headers = event.headers;
      headersReceived = true;
    }
    if (event.data && event.data.length > 0) {
      dataAccumulated.push(...event.data);
    }
    if (event.done) {
        dataAccumulated.unshift(headers);

        let sanitizedData = dataAccumulated.map(item => {
            let newItem = {...item};
            for(let key in newItem) {
                if(typeof newItem[key] === 'string') {
                    newItem[key] = parseISODate(newItem[key]);
                }
            }
            return Object.values(newItem);
        });
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(sanitizedData, { dateNF: "YYYY-MM-DD HH:MM:SS" });
        XLSX.utils.book_append_sheet(wb, ws, 'Data');
        const binaryData = XLSX.write(wb, { bookType: 'xlsx', type: 'binary' });
        const blob = new Blob([new Uint8Array([...binaryData].map(char => char.charCodeAt(0)))], { type: "application/octet-stream" });
        saveAs(blob, event.file_name + '.xlsx');
    }
});

function makeGetRequest(endpoint, params, msg) {
    $.get(endpoint, params, function(response) {
        console.log(msg);
    });
}

<!--Start of Tawk.to Script-->
var CHANNEL_ID = '64d0945994cf5d49dc68dd99';
var CHANNEL_NAME = 'CDV';
var Tawk_API = Tawk_API || {}, Tawk_LoadStart = new Date();
(function() {
    var s1 = document.createElement("script"),
        s0 = document.getElementsByTagName("script")[0];
    s1.async = true;
    s1.src = 'https://embed.tawk.to/' + CHANNEL_ID + '/1h77c6vne';
    s1.charset = 'UTF-8';
    s1.setAttribute('crossorigin', '*');
    s0.parentNode.insertBefore(s1, s0);
})();

function getUTMParameters() {
    var params = {};
    window.location.search.substring(1).split('&').forEach(function(pair) {
        var keyValue = pair.split('=');
        params[keyValue[0]] = decodeURIComponent(keyValue[1] || '');
    });
    return params;
}

var utmParams = getUTMParameters();
var referrer = document.referrer;

Tawk_API.onChatStarted = function() {
    if (typeof(gtag) !== 'undefined') {
        gtag('send', 'event', 'Tawk', 'Chat Started');
    }

    // Retrieve the Tawk chat details
    var tawkData = {
        chatId: Tawk_API.getChatId(),
        visitor: Tawk_API.getVisitorDetails(),
        message: {
            // Assuming you can get the latest message via a method, or gather this some other way.
            // The actual method/property to get the latest message might be different. Check Tawk's API.
            text: Tawk_API.getLastMessage() || "No message available"
        },
        time: new Date().toISOString(),  // Current time as an example, adjust as needed.
        event: 'chat:start',
        property: {
            id: CHANNEL_ID,
            name: CHANNEL_NAME
        }
    };

    // Send UTM, referrer, and Tawk data to backend
    var dataToSend = {
        utm: utmParams,
        referrer: referrer,
        tawk: tawkData
    };

    // socket.emit('client_message', {data: dataToSend});

    fetch('https://swiss-medica-2e0e7bc937df.herokuapp.com/tawk_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(dataToSend)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
    })
    .catch((error) => {
        console.error('Error:', error);
    });

};
<!--End of Tawk.to Script-->

$(document).ready(function() {
    const getAmoDataSm = () => makeGetRequest('/get_amo_data_sm', { time: $('#time-sm').val() }, 'get_amo_data_sm');
    const getAmoDataCdv = () => makeGetRequest('/get_amo_data_cdv', { time: $('#time-cdv').val() }, 'get_amo_data_cdv');
    const stopGetAmoDataSm = () => makeGetRequest('/stop_get_amo_data_sm', {}, 'stop_get_amo_data_sm');
    const stopGetAmoDataCdv = () => makeGetRequest('/stop_get_amo_data_cdv', {}, 'stop_get_amo_data_cdv');
    const startAutocalls = () => makeGetRequest('/start_autocalls', {}, 'start_autocalls');
    const setTelegramWebhooks = () => makeGetRequest('/set_telegram_webhooks', {}, 'set_telegram_webhooks');
    const buildPivotDataSm = () => makeGetRequest('/start_update_pivot_data_sm', {}, 'start_update_pivot_data_sm');
    const buildPivotDataCdv = () => makeGetRequest('/start_update_pivot_data_cdv', {}, 'start_update_pivot_data_cdv');
    const stopBuildPivotDataSm = () => makeGetRequest('/stop_update_pivot_data_sm', {}, 'start_update_pivot_data_sm');
    const stopBuildPivotDataCdv = () => makeGetRequest('/stop_update_pivot_data_cdv', {}, 'start_update_pivot_data_cdv');
    const downloadPivotDataSm = () => makeGetRequest('/data_excel_sm', {}, 'data_excel_sm');
    const downloadPivotDataCdv = () => makeGetRequest('/data_excel_cdv', {}, 'data_excel_cdv');

    $('#download_pivot_data_sm').on('click', downloadPivotDataSm);
    $('#download_pivot_data_cdv').on('click', downloadPivotDataCdv);
    $('#get_amo_data_sm').on('click', getAmoDataSm);
    $('#stop_get_amo_data_sm').on('click', stopGetAmoDataSm);
    $('#build_pivot_data_sm').on('click', buildPivotDataSm);
    $('#stop_build_pivot_data_sm').on('click', stopBuildPivotDataSm);
    $('#get_amo_data_cdv').on('click', getAmoDataCdv);
    $('#stop_get_amo_data_cdv').on('click', stopGetAmoDataCdv);
    $('#build_pivot_data_cdv').on('click', buildPivotDataCdv);
    $('#stop_build_pivot_data_cdv').on('click', stopBuildPivotDataCdv);
    $('#start_autocalls').on('click', startAutocalls);
    $('#set_telegram_webhooks').on('click', setTelegramWebhooks);
});