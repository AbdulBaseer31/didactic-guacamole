from __future__ import annotations

from typing import Any, Optional
from .types import ProposedAction, Observation, Element


class DynamicPlanner:
    """Plans actions by finding elements by role/name in current observation"""
    
    def __init__(self):
        self.state = "login_username"
    
    def find_element(self, obs: Observation, role: str, name_contains: str = "") -> Optional[Element]:
        for el in obs.elements:
            if el.role == role:
                if not name_contains or name_contains.lower() in el.name.lower():
                    return el
        return None
    
    def find_element_by_name(self, obs: Observation, name_contains: str) -> Optional[Element]:
        for el in obs.elements:
            if name_contains.lower() in el.name.lower():
                return el
        return None

    def propose_action(self, obs: Observation, goal: str, prev_action: Optional[ProposedAction] = None) -> ProposedAction:
        # Login flow
        if self.state == "login_username":
            el = self.find_element(obs, "textbox", "username")
            if el:
                self.state = "login_password"
                return ProposedAction(type="type", uix=el.uix, value="standard_user", reasoning="Enter username")
        
        if self.state == "login_password":
            el = self.find_element(obs, "textbox", "password")
            if el:
                self.state = "login_click"
                return ProposedAction(type="type", uix=el.uix, value="$SECRET:SAUCE_PASSWORD", reasoning="Enter password")
        
        if self.state == "login_click":
            el = self.find_element(obs, "button", "login")
            if el:
                self.state = "inventory"
                return ProposedAction(type="click", uix=el.uix, reasoning="Click login button")
        
        # Inventory - click "Add to cart" for backpack (first one)
        if self.state == "inventory":
            el = self.find_element(obs, "button", "add to cart")
            if el:
                self.state = "checkout"
                return ProposedAction(type="click", uix=el.uix, reasoning="Add Sauce Labs Backpack to cart")
            return ProposedAction(type="scroll", direction="down", reasoning="Scroll to find Add to cart")
        
        # After adding to cart, go to cart page
        if self.state == "checkout":
            el = self.find_element_by_name(obs, "cart")
            if not el:
                el = self.find_element(obs, "link", "cart")
            if el:
                self.state = "checkout_info"
                return ProposedAction(type="click", uix=el.uix, reasoning="Go to cart")
        
        # Click cart icon
        if self.state == "checkout":
            el = self.find_element_by_name(obs, "cart")
            if not el:
                el = self.find_element(obs, "link", "cart")
            if el:
                self.state = "checkout_info"
                return ProposedAction(type="click", uix=el.uix, reasoning="Go to cart")
        
        # Checkout page - click checkout button
        if self.state == "checkout_info":
            el = self.find_element(obs, "button", "checkout")
            if el:
                self.state = "fill_info"
                return ProposedAction(type="click", uix=el.uix, reasoning="Click checkout")
        
        # Fill first name
        if self.state == "fill_info":
            el = self.find_element(obs, "textbox", "first name")
            if not el:
                el = self.find_element(obs, "textbox", "firstname")
            if el:
                self.state = "fill_last"
                return ProposedAction(type="type", uix=el.uix, value="Ada", reasoning="Enter first name")
        
        # Fill last name
        if self.state == "fill_last":
            el = self.find_element(obs, "textbox", "last name")
            if not el:
                el = self.find_element(obs, "textbox", "lastname")
            if el:
                self.state = "fill_zip"
                return ProposedAction(type="type", uix=el.uix, value="Lovelace", reasoning="Enter last name")
        
        # Fill postal code
        if self.state == "fill_zip":
            el = self.find_element(obs, "textbox", "postal")
            if not el:
                el = self.find_element(obs, "textbox", "zip")
            if el:
                self.state = "continue_checkout"
                return ProposedAction(type="type", uix=el.uix, value="500001", reasoning="Enter postal code")
        
        # Continue
        if self.state == "continue_checkout":
            el = self.find_element(obs, "button", "continue")
            if el:
                self.state = "finish_order"
                return ProposedAction(type="click", uix=el.uix, reasoning="Continue checkout")
        
        # Finish
        if self.state == "finish_order":
            el = self.find_element(obs, "button", "finish")
            if el:
                self.state = "done"
                return ProposedAction(type="click", uix=el.uix, reasoning="Finish order")
        
        # Check for confirmation
        if self.state == "done":
            if "checkout-complete" in obs.url or "confirmation" in obs.title.lower() or self.find_element_by_name(obs, "thank you"):
                return ProposedAction(type="finish", success=True, reasoning="Order confirmed")
        
        # Fallback - scroll if stuck
        if self.find_element(obs, "button"):
            return ProposedAction(type="scroll", direction="down", reasoning="Scroll to find elements")
        
        return ProposedAction(type="finish", success=False, reasoning="Could not find next action")


def create_planner() -> DynamicPlanner:
    return DynamicPlanner()