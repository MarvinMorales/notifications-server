let dataRetrieved;

self.addEventListener('push', (event) => {
    try {
        // Verifica si los datos existen
        dataRetrieved = event.data.json();
        console.log("Push data:", dataRetrieved);
    } catch (e) {
        console.error("Error parsing push data:", e);
        dataRetrieved = { title: "Notificación", body: "Tienes una nueva notificación." }; // Fallback data
    }
    
    self.registration.showNotification(dataRetrieved.title, {
        body: dataRetrieved.body,
        requireInteraction: true,
        icon: 'https://static-00.iconduck.com/assets.00/archlinux-icon-2048x2048-q7549ths.png',
    });
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close(); // Cierra la notificación al hacer click

    const { survey_id } = dataRetrieved;
    const targetUrl = `https://agilevirtualassistants.com/?survey_id=${survey_id}`;
    event.waitUntil(clients.openWindow(targetUrl));
});

