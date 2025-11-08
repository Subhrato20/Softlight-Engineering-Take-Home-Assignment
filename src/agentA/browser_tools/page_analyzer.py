"""Page content analysis and extraction for LLM"""

from typing import List, Dict, Any
from playwright.sync_api import Page
import json


class PageAnalyzer:
    """Extracts and structures page content for LLM analysis"""
    
    def __init__(self, page: Page):
        """
        Initialize page analyzer.
        
        Args:
            page: Playwright Page object
        """
        self.page = page
    
    def get_page_text(self) -> str:
        """Get all visible text content from the page"""
        return self.page.evaluate("""
            () => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                let text = '';
                let node;
                while (node = walker.nextNode()) {
                    const parent = node.parentElement;
                    if (parent && 
                        parent.offsetParent !== null && 
                        !['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(parent.tagName)) {
                        text += node.textContent.trim() + ' ';
                    }
                }
                return text.trim();
            }
        """)
    
    def get_interactive_elements(self) -> List[Dict[str, Any]]:
        """
        Get all interactive elements (buttons, links, inputs, etc.) with descriptions.
        
        Returns:
            List of dictionaries with element information
        """
        return self.page.evaluate("""
            () => {
                const elements = [];
                
                // Buttons
                document.querySelectorAll('button, [role="button"]').forEach(btn => {
                    if (btn.offsetParent !== null) {
                        elements.push({
                            type: 'button',
                            text: btn.textContent.trim(),
                            aria_label: btn.getAttribute('aria-label') || '',
                            id: btn.id || '',
                            classes: Array.from(btn.classList).join(' '),
                            selector: btn.id ? `#${btn.id}` : 
                                     btn.className ? `.${Array.from(btn.classList)[0]}` : 
                                     `button:nth-of-type(${Array.from(document.querySelectorAll('button')).indexOf(btn) + 1})`
                        });
                    }
                });
                
                // Links
                document.querySelectorAll('a[href]').forEach(link => {
                    if (link.offsetParent !== null) {
                        elements.push({
                            type: 'link',
                            text: link.textContent.trim(),
                            href: link.href,
                            aria_label: link.getAttribute('aria-label') || '',
                            id: link.id || '',
                            classes: Array.from(link.classList).join(' '),
                            selector: link.id ? `#${link.id}` : 
                                     link.className ? `.${Array.from(link.classList)[0]}` : 
                                     `a[href="${link.getAttribute('href')}"]`
                        });
                    }
                });
                
                // Input fields
                document.querySelectorAll('input, textarea, select').forEach(input => {
                    if (input.offsetParent !== null) {
                        const label = input.labels ? 
                            (input.labels[0] ? input.labels[0].textContent.trim() : '') : 
                            (input.getAttribute('aria-label') || input.placeholder || '');
                        
                        elements.push({
                            type: input.tagName.toLowerCase(),
                            input_type: input.type || '',
                            placeholder: input.placeholder || '',
                            label: label,
                            name: input.name || '',
                            id: input.id || '',
                            classes: Array.from(input.classList).join(' '),
                            selector: input.id ? `#${input.id}` : 
                                     input.name ? `[name="${input.name}"]` :
                                     input.className ? `.${Array.from(input.classList)[0]}` : ''
                        });
                    }
                });
                
                return elements;
            }
        """)
    
    def analyze_page_state(self) -> Dict[str, Any]:
        """
        Get comprehensive page state for LLM analysis.
        
        Returns:
            Dictionary with page state information
        """
        return {
            "url": self.page.url,
            "title": self.page.title(),
            "visible_text": self.get_page_text()[:5000],  # Limit text length
            "interactive_elements": self.get_interactive_elements(),
            "modals_open": self._check_modals(),
            "forms_present": self._check_forms(),
            "page_loaded": self.page.evaluate("() => document.readyState === 'complete'")
        }
    
    def _check_modals(self) -> List[Dict[str, str]]:
        """Check if any modals/dialogs are open"""
        return self.page.evaluate("""
            () => {
                const modals = [];
                document.querySelectorAll('[role="dialog"], [role="alertdialog"], .modal, [class*="modal"]').forEach(modal => {
                    const style = window.getComputedStyle(modal);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        modals.push({
                            text: modal.textContent.trim().substring(0, 200),
                            role: modal.getAttribute('role') || '',
                            id: modal.id || ''
                        });
                    }
                });
                return modals;
            }
        """)
    
    def _check_forms(self) -> List[Dict[str, Any]]:
        """Check for forms on the page"""
        return self.page.evaluate("""
            () => {
                const forms = [];
                document.querySelectorAll('form').forEach(form => {
                    if (form.offsetParent !== null) {
                        const inputs = Array.from(form.querySelectorAll('input, textarea, select'))
                            .map(input => ({
                                type: input.type || input.tagName.toLowerCase(),
                                name: input.name || '',
                                placeholder: input.placeholder || '',
                                label: input.labels && input.labels[0] ? input.labels[0].textContent.trim() : ''
                            }));
                        
                        forms.push({
                            id: form.id || '',
                            action: form.action || '',
                            method: form.method || '',
                            inputs: inputs
                        });
                    }
                });
                return forms;
            }
        """)
    
    def get_page_content_for_llm(self) -> str:
        """
        Get formatted page content optimized for LLM analysis.
        
        Returns:
            JSON string with structured page information
        """
        state = self.analyze_page_state()
        return json.dumps(state, indent=2)

