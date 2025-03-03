LOCATORS = {
    "job_cards": "[data-view-name='job-card']",
    "job_title": ".artdeco-entity-lockup__title a span[aria-hidden='true']",
    "job_location": ".artdeco-entity-lockup__caption span",
    "job_keyword_search": "input.basic-input.jobs-search-box__text-input.jobs-search-box__keyboard-text-input",
    "job_location_search": "input[aria-label='City, state, or zip code']",
    "search_button": ".jobs-search-box__submit-button",
    "company": ".artdeco-entity-lockup__subtitle span",
    "pagination_list": ".artdeco-pagination__pages",
    "pagination_button": lambda page_num: f'[aria-label="Page {page_num}"]',
    "more_pagination_buttons": lambda page_num: f'button[aria-label="Page {page_num}"]'
}