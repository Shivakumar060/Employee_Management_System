/**
 * ApexCorp - Production-Grade Platform JS logic
 * Interactivity: Search, Filter, Sort, Dark Mode, Toasts
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Dark Mode Toggle & Persistence
    const darkModeToggle = document.getElementById('darkModeToggle');
    const htmlElement = document.documentElement;
    const bodyElement = document.body;
    
    // Check saved preference or system preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        htmlElement.setAttribute('data-bs-theme', savedTheme);
        updateIcon(savedTheme);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        htmlElement.setAttribute('data-bs-theme', 'dark');
        updateIcon('dark');
    }

    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', () => {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            htmlElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateIcon(newTheme);
        });
    }

    function updateIcon(theme) {
        const icon = darkModeToggle.querySelector('i');
        if (theme === 'dark') {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
    }

    // 2. Toast Initialization
    const toastElList = [].slice.call(document.querySelectorAll('.toast'));
    const toastList = toastElList.map(function(toastEl) {
        const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
        toast.show();
        return toast;
    });

    // 3. Advanced Filtering & Sorting for Directory
    const searchInput = document.getElementById('searchInput');
    const filterDept = document.getElementById('filterDept');
    const filterSalary = document.getElementById('filterSalary');
    const sortOrder = document.getElementById('sortOrder');
    const directoryBody = document.getElementById('directoryBody');
    const rows = Array.from(directoryBody ? directoryBody.getElementsByTagName('tr') : []);

    function filterAndSort() {
        if (!directoryBody) return;
        
        let filteredRows = rows.filter(row => {
            const name = row.getAttribute('data-name').toLowerCase();
            const dept = row.getAttribute('data-dept');
            const salary = parseFloat(row.getAttribute('data-salary'));
            
            const searchMatch = name.includes(searchInput.value.toLowerCase());
            const deptMatch = filterDept.value === 'all' || dept === filterDept.value;
            let salaryMatch = true;
            if (filterSalary.value === 'low') salaryMatch = salary < 40000;
            if (filterSalary.value === 'high') salaryMatch = salary >= 40000;

            return searchMatch && deptMatch && salaryMatch;
        });

        // Sorting
        if (sortOrder.value === 'name') {
            filteredRows.sort((a, b) => a.getAttribute('data-name').localeCompare(b.getAttribute('data-name')));
        } else if (sortOrder.value === 'salary_desc') {
            filteredRows.sort((a, b) => parseFloat(b.getAttribute('data-salary')) - parseFloat(a.getAttribute('data-salary')));
        }

        // Apply display
        rows.forEach(r => r.style.display = 'none');
        filteredRows.forEach(r => {
            r.style.display = '';
            directoryBody.appendChild(r); // Re-append for sorting order
        });
    }

    if (searchInput) {
        [searchInput, filterDept, filterSalary, sortOrder].forEach(el => {
            el.addEventListener('input', filterAndSort);
        });
    }

    // 4. Modal Data Transfer
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        deleteModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const id = button.getAttribute('data-id');
            const name = button.getAttribute('data-name');
            const nameSpan = document.getElementById('deleteEmployeeName');
            const deleteForm = document.getElementById('deleteForm');
            nameSpan.textContent = name;
            deleteForm.action = `/delete/${id}`;

        });
    }
});
