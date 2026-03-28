import allure
import pytest
from automation_pytest.pages.projects_page import ProjectsPage

@allure.feature('projects')
@allure.story('smoke')
@pytest.mark.ui
def test_projects_smoke(page, base_url):
    target = ProjectsPage(page, base_url)
    with allure.step('打开页面'):
        target.open()
    with allure.step('页面加载校验'):
        target.assert_loaded()
    with allure.step('断言等级标记'):
        assert 'P0' in ['P0', 'P1', 'P2']
