document.addEventListener('DOMContentLoaded', () => {

    // --- Configuration ---
    // Using relative path '/api' allows it to work on localhost and deployed Azure implementations 
    // where the UI handles the 'api' prefix naturally or is hosted under same domain.
    const API_BASE_URL = "/api";

    // --- Elements ---
    const btnUpload = document.getElementById('btn-upload');
    const btnDeleteCat = document.getElementById('btn-delete-cat');
    const fileInput = document.getElementById('pdf-file');
    const uploadCategorySelect = document.getElementById('upload-category'); // New element
    const uploadStatus = document.getElementById('upload-status');
    const newCategoryGroup = document.getElementById('new-category-group');
    const newCategoryInput = document.getElementById('new-category-input');

    const btnAsk = document.getElementById('btn-ask');
    const txtQuestion = document.getElementById('question');
    const selCategory = document.getElementById('category'); // Chat category
    const chatStatus = document.getElementById('chat-status');
    const answerSection = document.getElementById('answer-section');
    const answerContent = document.getElementById('answer-content');
    const answerSources = document.getElementById('answer-sources');


    // --- 0. Dynamic Category Loading ---
    async function loadCategories() {
        try {
            const response = await fetch(`${API_BASE_URL}/categories`);
            if (!response.ok) return;

            const data = await response.json();
            const categories = data.categories || [];

            // 1. Populate Upload Dropdown
            // Keep "Uncategorized" and "New Category" logic
            // We want: [Uncategorized, ...FetchedCats..., + Add New]
            uploadCategorySelect.innerHTML = '';

            // Fixed first option
            const optUncat = document.createElement('option');
            optUncat.value = "uncategorized";
            optUncat.textContent = "Uncategorized";
            uploadCategorySelect.appendChild(optUncat);

            // Dynamic options
            categories.forEach(cat => {
                if (cat.toLowerCase() === "uncategorized") return; // skip if duplicate

                const opt = document.createElement('option');
                opt.value = cat;
                opt.textContent = cat;
                uploadCategorySelect.appendChild(opt);
            });

            // Fixed last option
            const optNew = document.createElement('option');
            optNew.value = "new_category_option";
            optNew.textContent = "+ Add New Category";
            uploadCategorySelect.appendChild(optNew);


            // 2. Populate Chat Dropdown
            // We want: [All (Global), ...FetchedCats...]
            selCategory.innerHTML = '';

            const optAll = document.createElement('option');
            optAll.value = "";
            optAll.textContent = "All (Global Search)";
            selCategory.appendChild(optAll);

            categories.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat;
                opt.textContent = cat;
                selCategory.appendChild(opt);
            });

        } catch (err) {
            console.error("Failed to load categories", err);
        }
    }

    // Initial Load
    loadCategories();

    // Toggle "New Category" input
    uploadCategorySelect.addEventListener('change', () => {
        if (uploadCategorySelect.value === 'new_category_option') {
            newCategoryGroup.style.display = 'block';
            newCategoryInput.focus();
        } else {
            newCategoryGroup.style.display = 'none';
        }
    });

    // --- 1. Upload Logic (REAL) ---
    btnUpload.addEventListener('click', async () => {
        const files = fileInput.files;

        // Determine category
        let category = uploadCategorySelect ? uploadCategorySelect.value : "uncategorized";
        if (category === 'new_category_option') {
            const typedCat = newCategoryInput.value.trim();
            if (!typedCat) {
                showStatus(uploadStatus, 'Please enter a name for the new category.', 'error');
                return;
            }
            category = typedCat; // Use the typed value
        }

        if (files.length === 0) {
            showStatus(uploadStatus, 'Please select at least one PDF file.', 'error');
            return;
        }

        // Validate all are PDFs
        for (let i = 0; i < files.length; i++) {
            if (files[i].type !== 'application/pdf') {
                showStatus(uploadStatus, `File '${files[i].name}' is not a PDF.`, 'error');
                return;
            }
        }

        showStatus(uploadStatus, `Uploading ${files.length} file(s)...`, 'loading');

        try {
            const formData = new FormData();
            formData.append('category', category);

            // Append all files with unique keys to ensure backend captures all
            for (let i = 0; i < files.length; i++) {
                formData.append(`file_${i}`, files[i]);
            }

            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || `Server Error: ${response.status}`);
            }

            const result = await response.json();
            showStatus(uploadStatus, result.message || 'Upload successful!', 'success');

            // Clear input
            // Clear input
            fileInput.value = '';
            newCategoryInput.value = '';

            // If a new category was created, we need to refresh the list and select it
            if (newCategoryGroup.style.display === 'block') {
                newCategoryGroup.style.display = 'none'; // hide input

                // Reload categories to reflect the new one in all dropdowns
                await loadCategories();

                // Select the newly added category in the dropdown
                const options = Array.from(uploadCategorySelect.options);
                const matchingOption = options.find(opt => opt.value.toLowerCase() === category.toLowerCase());
                if (matchingOption) {
                    uploadCategorySelect.value = matchingOption.value;
                }
            }

        } catch (err) {
            console.error(err);
            showStatus(uploadStatus, 'Upload failed: ' + err.message, 'error');
        }
    });


    // --- 2. Chat Logic (REAL) ---
    btnAsk.addEventListener('click', async () => {
        const question = txtQuestion.value.trim();
        const category = selCategory.value;

        if (!question) {
            showStatus(chatStatus, 'Please enter a question.', 'error');
            return;
        }

        showStatus(chatStatus, 'Thinking...', 'loading');
        answerSection.style.display = 'none';
        btnAsk.disabled = true;

        try {
            const payload = {
                question: question,
                category: category || null
            };

            const response = await fetch(`${API_BASE_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Server Error: ${response.status}`);
            }

            const data = await response.json();

            // Display Answer
            displayAnswer(data);
            showStatus(chatStatus, '', 'hidden');

        } catch (err) {
            console.error(err);
            showStatus(chatStatus, 'Error: ' + err.message, 'error');
        } finally {
            btnAsk.disabled = false;
        }
    });

    // --- Helpers ---

    function showStatus(element, message, type) {
        element.textContent = message;
        element.className = `status ${type}`;
        if (type === 'hidden') {
            element.style.display = 'none';
        } else {
            element.style.display = 'block';
        }
    }



    // 1. Add Delete Listener
    // --- 3. Delete Logic (Danger Zone) ---
    const radioDeleteOptions = document.getElementsByName('deleteOption');
    const containerDelCategory = document.getElementById('del-opt-category');
    const containerDelPdf = document.getElementById('del-opt-pdf');

    const delCategorySelect = document.getElementById('del-category-select');

    const delPdfCatSelect = document.getElementById('del-pdf-cat-select');
    const delPdfFileSelect = document.getElementById('del-pdf-file-select');

    const btnExecuteDelete = document.getElementById('btn-execute-delete');
    const deleteStatus = document.getElementById('delete-status');

    // Helper to fetch and populate categories
    async function loadDeleteCategories() {
        if (!delCategorySelect || !delPdfCatSelect) return;

        try {
            const response = await fetch(`${API_BASE_URL}/list_pdfs?type=categories`);
            if (!response.ok) return; // Silent fail or handle better

            const data = await response.json();
            const categories = data.categories || [];

            // Populate Dropdowns
            [delCategorySelect, delPdfCatSelect].forEach(sel => {
                sel.innerHTML = '<option value="">-- Select Category --</option>';
                categories.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat;
                    opt.textContent = cat;
                    sel.appendChild(opt);
                });
            });

        } catch (err) {
            console.error("Failed to load categories for delete", err);
        }
    }

    // Load categories on init
    loadDeleteCategories();


    // Toggle Visibility
    radioDeleteOptions.forEach(rb => {
        rb.addEventListener('change', () => {
            if (rb.value === 'category') {
                containerDelCategory.classList.remove('hidden');
                containerDelPdf.classList.add('hidden');
            } else {
                containerDelCategory.classList.add('hidden');
                containerDelPdf.classList.remove('hidden');
            }
            // Clear status when switching
            showStatus(deleteStatus, '', 'hidden');
        });
    });

    // Populate PDF Dropdown when Category Changes
    if (delPdfCatSelect) {
        delPdfCatSelect.addEventListener('change', async () => {
            const category = delPdfCatSelect.value;

            // Reset PDF select
            delPdfFileSelect.innerHTML = '<option value="">(Loading...)</option>';
            delPdfFileSelect.disabled = true;

            if (!category) {
                delPdfFileSelect.innerHTML = '<option value="">(Select Category First)</option>';
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/list_pdfs?category=${category}`);
                if (!response.ok) throw new Error('Failed to fetch PDFs');

                const data = await response.json();
                const pdfs = data.pdfs || [];

                delPdfFileSelect.innerHTML = '<option value="">-- Select PDF --</option>';
                if (pdfs.length === 0) {
                    delPdfFileSelect.innerHTML += '<option value="" disabled>No PDFs found</option>';
                } else {
                    pdfs.forEach(pdf => {
                        const opt = document.createElement('option');
                        opt.value = pdf;
                        opt.textContent = pdf;
                        delPdfFileSelect.appendChild(opt);
                    });
                    delPdfFileSelect.disabled = false;
                }

            } catch (err) {
                console.error(err);
                delPdfFileSelect.innerHTML = '<option value="">Error loading PDFs</option>';
            }
        });
    }

    // Execute Delete
    if (btnExecuteDelete) {
        btnExecuteDelete.addEventListener('click', async () => {
            const mode = document.querySelector('input[name="deleteOption"]:checked').value;

            let category = "";
            let pdfName = "";
            let confirmMsg = "";

            if (mode === 'category') {
                category = delCategorySelect.value;
                if (!category) {
                    showStatus(deleteStatus, 'Please select a category to wipe.', 'error');
                    return;
                }
                confirmMsg = `Are you sure you want to delete ALL data for category '${category}'? This cannot be undone.`;
            } else {
                category = delPdfCatSelect.value;
                pdfName = delPdfFileSelect.value;

                if (!category) {
                    showStatus(deleteStatus, 'Please select a category.', 'error');
                    return;
                }
                if (!pdfName) {
                    showStatus(deleteStatus, 'Please select a PDF file.', 'error');
                    return;
                }
                confirmMsg = `Are you sure you want to delete PDF '${pdfName}' from '${category}'?`;
            }

            if (!confirm(confirmMsg)) {
                return;
            }

            showStatus(deleteStatus, 'Deleting...', 'loading');

            try {
                let url = `${API_BASE_URL}/delete_category?category=${category}`;
                if (mode === 'pdf') {
                    // Send pdf_name in body or query. Let's use query for simplicity if API supports it, 
                    // otherwise body. I configured backend to check both.
                    url += `&pdf_name=${encodeURIComponent(pdfName)}`;
                }

                const response = await fetch(url, { method: 'DELETE' });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(errorText || `Server Error: ${response.status}`);
                }

                const result = await response.json();
                showStatus(deleteStatus, result.message, 'success');

                // Refresh list if we just deleted a PDF
                if (mode === 'pdf') {
                    // Trigger change event to reload list
                    delPdfCatSelect.dispatchEvent(new Event('change'));
                }

                // Reload categories in case we wiped a category entirely (optional, but good UX)
                if (mode === 'category') {
                    // Slight delay to allow backend to update if needed
                    setTimeout(loadDeleteCategories, 1000);
                }

            } catch (err) {
                console.error(err);
                showStatus(deleteStatus, 'Delete failed: ' + err.message, 'error');
            }
        });
    }

    // ...

    function displayAnswer(data) {
        answerSection.style.display = 'block';
        answerContent.textContent = data.answer || "No answer received.";

        // Render MathJax if available
        if (window.MathJax) {
            window.MathJax.typesetPromise([answerContent]).then(() => {
                // Formatting complete
            }).catch((err) => console.error("MathJax error:", err));
        }

        const results = data.results || [];

        if (results.length > 0) {
            // Deduplicate by File + Page for cleaner view
            const uniqueMap = new Map();
            results.forEach(r => {
                const key = `${r.pdf_name}:${r.page}`;
                if (!uniqueMap.has(key)) {
                    uniqueMap.set(key, r);
                }
            });

            let html = `
                <div style="margin-top: 15px;">
                    <strong>Sources Used:</strong>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em;">
                        <thead>
                            <tr style="background: #f4f4f4; text-align: left;">
                                <th style="border: 1px solid #ddd; padding: 6px;">File</th>
                                <th style="border: 1px solid #ddd; padding: 6px;">Category</th>
                                <th style="border: 1px solid #ddd; padding: 6px;">Year</th>
                                <th style="border: 1px solid #ddd; padding: 6px;">Page</th>
                                <th style="border: 1px solid #ddd; padding: 6px;">Action</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            for (const r of uniqueMap.values()) {
                html += `
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 6px;">${r.pdf_name}</td>
                        <td style="border: 1px solid #ddd; padding: 6px;">${r.category}</td>
                        <td style="border: 1px solid #ddd; padding: 6px;">${r.year}</td>
                        <td style="border: 1px solid #ddd; padding: 6px;">${r.page}</td>
                        <td style="border: 1px solid #ddd; padding: 6px;">
                            <a href="${r.download_url}" target="_blank" style="color: #007bff; text-decoration: none;">Download</a>
                        </td>
                    </tr>
                `;
            }

            html += `</tbody></table></div>`;
            answerSources.innerHTML = html;

        } else if (data.sources && data.sources.length > 0) {
            const uniqueSources = [...new Set(data.sources)];
            answerSources.innerHTML = `<strong>Sources:</strong> ${uniqueSources.join(', ')}`;
        } else {
            answerSources.textContent = "No sources found.";
        }
    }

    // --- Accordion Logic ---
    window.toggleAccordion = function (index) {
        const contents = document.querySelectorAll('.accordion-content');
        const headers = document.querySelectorAll('.accordion-header');

        contents.forEach((content, i) => {
            if (i === index) {
                // Toggle current
                if (content.classList.contains('active')) {
                    content.classList.remove('active');
                    headers[i].classList.remove('active');
                } else {
                    content.classList.add('active');
                    headers[i].classList.add('active');
                }
            } else {
                // Close others
                content.classList.remove('active');
                headers[i].classList.remove('active');
            }
        });
    }

});
