'use strict';

describe('Controller: ScotusCtrl', function () {

  // load the controller's module
  beforeEach(module('scotusChatApp'));

  var ScotusCtrl, scope;

  // Initialize the controller and a mock scope
  beforeEach(inject(function ($controller, $rootScope) {
    scope = $rootScope.$new();
    ScotusCtrl = $controller('ScotusCtrl', {
      $scope: scope
    });
  }));

  it('should ...', function () {
    expect(1).toEqual(1);
  });
});
