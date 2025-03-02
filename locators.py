SELECTORS = {
    "job_cards": "[data-view-name='job-card']",
    "job_title": ".artdeco-entity-lockup__title a span",
    "job_location": ".artdeco-entity-lockup__caption span",
    "company": ".artdeco-entity-lockup__subtitle span",
    "pagination_list": ".artdeco-pagination__pages",
    "pagination_button": lambda page_num: f'[data-test-pagination-page-btn="{page_num}"] button'
}