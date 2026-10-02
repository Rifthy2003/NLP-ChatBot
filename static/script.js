const form = document.getElementById("composer");
const input = document.getElementById("user-input");
const log = document.getElementById("log");
const sendButton = document.getElementById("send-btn");


form.addEventListener("submit", async function (event) {

    event.preventDefault();

    const text = input.value.trim();

    if (!text) {
        return;
    }

    // Display customer message
    addMessage(text, "user");

    input.value = "";
    sendButton.disabled = true;
    sendButton.textContent = "Searching...";

    try {

        const response = await fetch("/api/search", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                text: text
            })
        });


        const data = await response.json();

        if (!response.ok) {
            addMessage(data.error || "Something went wrong.", "bot");
            return;
        }

        displayResults(data.found, data.not_found);

    } catch (error) {

        addMessage(
            "Unable to connect to the server.",
            "bot"
        );

    } finally {

        sendButton.disabled = false;
        sendButton.textContent = "Find Items";

        input.focus();
    }
});


function addMessage(text, type) {

    const message = document.createElement("div");

    message.className = `msg ${type}`;

    const bubble = document.createElement("div");

    bubble.className = "bubble";
    bubble.textContent = text;

    message.appendChild(bubble);

    log.appendChild(message);

    scrollToBottom();
}


function displayResults(found, notFound) {

    const message = document.createElement("div");

    message.className = "msg bot";


    const bubble = document.createElement("div");

    bubble.className = "bubble result-bubble";


    // No products found
    if (found.length === 0) {

        const text = document.createElement("p");

        text.textContent =
            "Sorry, I couldn't find those products in the supermarket.";

        bubble.appendChild(text);

    } else {

        const title = document.createElement("strong");

        title.textContent = "Your Shelf List";

        bubble.appendChild(title);


        const results = document.createElement("div");

        results.className = "results";


        found.forEach(function (item) {

            const tag = document.createElement("div");

            tag.className = "tag";


            const name = document.createElement("div");

            name.className = "tag-name";

            name.textContent = item.product;


            const aisle = document.createElement("div");

            aisle.className = "tag-aisle";

            aisle.textContent = item.aisle;


            const shelf = document.createElement("div");

            shelf.className = "tag-shelf";

            shelf.textContent = item.shelf;


            tag.appendChild(name);
            tag.appendChild(aisle);
            tag.appendChild(shelf);

            results.appendChild(tag);
        });


        bubble.appendChild(results);
    }


    // Display products that were not found
    if (notFound.length > 0) {

        const missing = document.createElement("div");

        missing.className = "miss-list";

        missing.innerHTML =
            "<strong>Items not found:</strong><br>";


        notFound.forEach(function (item) {

            const span = document.createElement("span");

            span.textContent = item;

            missing.appendChild(span);
        });


        bubble.appendChild(missing);
    }


    // Add Print Shelf List button only when products were found
    if (found.length > 0) {

        const actions = document.createElement("div");

        actions.className = "receipt-actions";


        const printButton = document.createElement("button");

        printButton.type = "button";

        printButton.textContent = "Print Shelf List";


        printButton.addEventListener("click", function () {

            printShelfList(found, notFound);

        });


        actions.appendChild(printButton);

        bubble.appendChild(actions);
    }


    message.appendChild(bubble);

    log.appendChild(message);

    scrollToBottom();
}


// Print only the current shelf list
function printShelfList(found, notFound) {

    let items = "";


    found.forEach(function (item) {

        items += `
            <tr>
                <td>${escapeHTML(item.product)}</td>
                <td>${escapeHTML(item.shelf)}</td>
                <td>${escapeHTML(item.aisle)}</td>
            </tr>
        `;
    });


    let missingItems = "";


    if (notFound.length > 0) {

        missingItems = `
            <div class="missing">
                <strong>Items not found:</strong>
                ${notFound.map(item => escapeHTML(item)).join(", ")}
            </div>
        `;
    }


    const printWindow = window.open("", "_blank", "width=700,height=700");


    if (!printWindow) {

        alert("Please allow pop-ups to print the shelf list.");

        return;
    }


    printWindow.document.write(`
        <!DOCTYPE html>

        <html>

        <head>

            <title>Supermarket Shelf List</title>

            <style>

                body {
                    font-family: Arial, sans-serif;
                    padding: 30px;
                    color: #222;
                }

                h1 {
                    text-align: center;
                    color: #2e7d32;
                }

                .date {
                    text-align: center;
                    color: #666;
                    margin-bottom: 25px;
                }

                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }

                th,
                td {
                    border: 1px solid #ccc;
                    padding: 12px;
                    text-align: left;
                }

                th {
                    background: #2e7d32;
                    color: white;
                }

                .missing {
                    margin-top: 20px;
                    color: #b3261e;
                }

                .thank-you {
                    text-align: center;
                    margin-top: 30px;
                }

            </style>

        </head>


        <body>

            <h1>Supermarket Assistant</h1>

            <div class="date">
                Shelf Location List
            </div>


            <table>

                <thead>

                    <tr>
                        <th>Product</th>
                        <th>Shelf</th>
                        <th>Aisle / Category</th>
                    </tr>

                </thead>


                <tbody>

                    ${items}

                </tbody>

            </table>


            ${missingItems}


            <p class="thank-you">
                Thank you for shopping with us!
            </p>

        </body>

        </html>
    `);


    printWindow.document.close();

    printWindow.focus();


    setTimeout(function () {

        printWindow.print();

    }, 300);
}


function escapeHTML(value) {

    const div = document.createElement("div");

    div.textContent = String(value);

    return div.innerHTML;
}


function scrollToBottom() {

    log.scrollTop = log.scrollHeight;
}