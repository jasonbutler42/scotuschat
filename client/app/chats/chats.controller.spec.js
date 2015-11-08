'use strict';

describe('Controller: ChatsCtrl', function () {

  // load the controller's module
  beforeEach(module('scotusChatApp'));

  var ChatsCtrl, scope;

  // Initialize the controller and a mock scope
  beforeEach(inject(function ($controller, $rootScope) {
    scope = $rootScope.$new();
    ChatsCtrl = $controller('ChatsCtrl', {
      $scope: scope
    });
  }));

  it('should ...', function () {
    expect(1).toEqual(1);
  });
});
