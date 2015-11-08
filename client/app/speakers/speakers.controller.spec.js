'use strict';

describe('Controller: SpeakersCtrl', function () {

  // load the controller's module
  beforeEach(module('scotusChatApp'));

  var SpeakersCtrl, scope;

  // Initialize the controller and a mock scope
  beforeEach(inject(function ($controller, $rootScope) {
    scope = $rootScope.$new();
    SpeakersCtrl = $controller('SpeakersCtrl', {
      $scope: scope
    });
  }));

  it('should ...', function () {
    expect(1).toEqual(1);
  });
});
