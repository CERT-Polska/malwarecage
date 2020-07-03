describe('Login test - Malwarecage', function() {
   it('Visit malwarecage', function () {
       cy.visit('http://malwarefront:80')

       cy.url()
           .should('include', '/login')

       cy.get(':nth-child(1) > .form-control')
           .type('admin')
           .should('have.value', 'admin')

       cy.get(':nth-child(2) > .form-control')
           .type('Your password')
           .should('have.value', 'Your password')

       cy.contains('Submit').click()
       cy.contains('Logged as: admin')

       cy.contains('Logout').click()
   })
})
